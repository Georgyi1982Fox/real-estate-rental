"""CLI парсера: ``bina-scrape --source myhome --limit 100``."""

import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click
import structlog

from bina.application.daily_report import DailyReport, report_day
from bina.application.health_monitor import Alert, HealthMonitor
from bina.application.ports.embeddings import EmbeddingsError
from bina.application.ports.scraper import BaseScraper
from bina.application.rent_reminders import TBILISI
from bina.application.use_cases.agencies import run_bumps
from bina.application.use_cases.analyze_photos import AnalyzePhotosUseCase, PhotoStats
from bina.application.use_cases.check_fraud import CheckFraudUseCase, FraudStats
from bina.application.use_cases.embed_listings import EmbedListingsUseCase, EmbedStats
from bina.application.use_cases.find_duplicates import DuplicateStats, FindDuplicatesUseCase
from bina.application.use_cases.geocode_listings import GeocodeListingsUseCase, GeocodeStats
from bina.application.use_cases.notifications import (
    CreatedNotifications,
    CreateNotificationsUseCase,
    DeliverNotificationsUseCase,
    DeliveryStats,
)
from bina.application.use_cases.premium_reminders import (
    PremiumReminderStats,
    PremiumRemindersUseCase,
)
from bina.application.use_cases.rent_reminders import (
    RentReminderStats,
    SendRentRemindersUseCase,
)
from bina.application.use_cases.translate_listings import (
    TranslateListingsUseCase,
    TranslationStats,
)
from bina.infrastructure.db.locks import FRAUD_LOCK, TRANSLATE_LOCK, advisory_lock
from bina.infrastructure.db.repositories.admin import AdminRepository
from bina.infrastructure.db.repositories.agencies import AgenciesRepository
from bina.infrastructure.db.repositories.districts import DistrictsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.notifications import (
    NotificationsRepository,
    SavedSearchesRepository,
)
from bina.infrastructure.db.repositories.photo_reports import PhotoReportsRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from bina.infrastructure.db.session.manager import DatabaseManager
from bina.infrastructure.llm.fraud_analyzer import LLMFraudAnalyzer
from bina.infrastructure.llm.listing_extractor import LLMListingExtractor
from bina.infrastructure.llm.llm_factory import LLMFactory, embeddings_configured
from bina.infrastructure.llm.photo_analyzer import (
    create_photo_analyzer,
    photo_analysis_configured,
)
from bina.infrastructure.llm.translator import LLMTranslator
from bina.infrastructure.scrapers.backfill import BackfillStats, DetailsSource, backfill_details
from bina.infrastructure.scrapers.korter_scraper import KorterScraper
from bina.infrastructure.scrapers.livo_scraper import LivoScraper
from bina.infrastructure.scrapers.myhome_scraper import MyHomeScraper
from bina.infrastructure.scrapers.pipeline import ScrapeResult, run_scrape
from bina.infrastructure.scrapers.scheduler import ScraperScheduler
from bina.infrastructure.scrapers.settings import ScraperSettings, TelegramSettings
from bina.infrastructure.scrapers.ss_scraper import SSScraper
from bina.infrastructure.scrapers.telegram_scraper import TelegramChannelScraper

if TYPE_CHECKING:
    from aiogram.client.default import DefaultBotProperties

logger = structlog.get_logger(__name__)

# Сайты (у них есть страницы объявлений для дозагрузки и перепроверки)
SOURCES = ("myhome", "ss", "livo", "korter")
# TASK-091: публичные Telegram-каналы (нужен AI: LLM_API_KEY)
TELEGRAM = "telegram"
# Перевод коммитится пачками: сбой посередине не теряет уже сделанное
TRANSLATE_BATCH = 20
# Сколько объявлений с текстом не на своём языке исправлять за запуск
LANGUAGE_FIX_BATCH = 5000
# Сколько объявлений AI переводит/проверяет одновременно (LLM_CONCURRENCY)
LLM_CONCURRENCY = max(1, int(os.getenv("LLM_CONCURRENCY", "") or 5))
# Отправка уведомлений пачками (коммит после каждой)
DELIVERY_BATCH = 100
# Сколько объявлений проверять на дубликаты за запуск по расписанию
DUPLICATES_BATCH = 2000
# Адресов на карте за запуск: геокодер — не чаще 1 запроса в секунду
GEOCODE_BATCH = 30
# Отпечатков смысла за запуск (TASK-012): 500 объявлений ≈ 16 запросов, копейки
EMBED_BATCH = 500


def make_scraper(source: str, *, details: bool, dump_dir: Path | None) -> BaseScraper:
    """Создаёт парсер источника с настройками из окружения."""
    common = {
        "delay_seconds": ScraperSettings.SCRAPE_DELAY_SECONDS,
        "user_agents": ScraperSettings.SCRAPE_USER_AGENTS,
    }
    if source == "myhome":
        return MyHomeScraper(**common, fetch_details=details, dump_dir=dump_dir)  # type: ignore[arg-type]
    if source == "ss":
        return SSScraper(**common, fetch_details=details, dump_dir=dump_dir)  # type: ignore[arg-type]
    if source == "livo":
        return LivoScraper(**common, fetch_details=details, dump_dir=dump_dir)  # type: ignore[arg-type]
    if source == "korter":
        return KorterScraper(**common, fetch_details=details, dump_dir=dump_dir)  # type: ignore[arg-type]
    if source == TELEGRAM:
        # Без AI посты не разобрать: карточки без цены отбросит нормализатор
        extractor = LLMListingExtractor(LLMFactory.create_provider()) if details else None
        return TelegramChannelScraper(extractor, **common)  # type: ignore[arg-type]
    raise click.BadParameter(f"unknown source {source!r}")


def scrape_sources() -> list[str]:
    """Источники парсинга по расписанию: сайты и, если есть AI и каналы, Telegram."""
    sources = list(SOURCES)
    if llm_configured() and TelegramSettings.CHANNELS:
        sources.append(TELEGRAM)
    return sources


async def scrape(
    sources: list[str],
    limit: int,
    *,
    details: bool = True,
    dump_dir: Path | None = None,
) -> list[ScrapeResult]:
    """Парсит источники по очереди и сохраняет результат в БД (``DATABASE_URL``)."""
    db = DatabaseManager()
    results: list[ScrapeResult] = []
    try:
        await _merge_street_districts(db)
        for source in sources:
            scraper = make_scraper(source, details=details, dump_dir=dump_dir)
            try:
                results.append(await run_scrape(scraper, source, limit, db.session_factory))
                if source == TELEGRAM:
                    await _archive_old_posts(db)
            finally:
                close = getattr(scraper, "close", None)
                if close is not None:
                    await close()
    finally:
        await db.dispose()
    return results


async def _merge_street_districts(db: DatabaseManager) -> None:
    """Чистка сохранённых данных перед сбором.

    «Сабуртало/Картозия» → «Сабуртало»; цены, ошибочно указанные хозяевами на сайтах:
    «посуточно» с месячной ценой и аренда с ценой продажи.
    """
    async with db.session_factory() as session:
        merged = await DistrictsRepository(session).merge_streets()
        to_monthly, sale_prices = await ListingsRepository(session).fix_impossible_prices()
        await session.commit()
    if merged:
        logger.info("Street districts merged", districts=merged)
    if to_monthly or sale_prices:
        logger.info("Impossible prices fixed", to_monthly=to_monthly, archived=sale_prices)


@click.group(invoke_without_command=True)
@click.option(
    "--source",
    type=click.Choice([*SOURCES, TELEGRAM, "all"]),
    help="Источник объявлений.",
)
@click.option(
    "--limit",
    default=50,
    show_default=True,
    type=click.IntRange(1, 1000),
    help="Максимум объявлений с каждого источника.",
)
@click.option(
    "--details/--no-details",
    default=True,
    show_default=True,
    help="Открывать страницу каждого объявления (фото, телефон, имя).",
)
@click.option(
    "--dump-dir",
    type=click.Path(path_type=Path, file_okay=False),
    help="Сохранить сырой HTML первой страницы списка и объявления (MyHome).",
)
@click.pass_context
def cli(
    ctx: click.Context,
    source: str | None,
    limit: int,
    details: bool,
    dump_dir: Path | None,
) -> None:
    """Парсинг объявлений недвижимости (MyHome.ge, SS.ge) в БД.

    Пример: bina-scrape --source myhome --limit 100
    """
    if ctx.invoked_subcommand is not None:
        return
    if source is None:
        raise click.UsageError("Укажите --source (myhome, ss, livo, korter, telegram или all)")

    sources = scrape_sources() if source == "all" else [source]
    results = asyncio.run(scrape(sources, limit, details=details, dump_dir=dump_dir))
    _echo_results(results)


def llm_configured() -> bool:
    """Задан ли ключ AI (``LLM_API_KEY``)."""
    return bool(os.getenv("LLM_API_KEY"))


class TranslationBusyError(RuntimeError):
    """Перевод уже идёт в другом процессе (например, в сервисе ``scraper``)."""


async def _archive_old_posts(db: DatabaseManager) -> None:
    """Посты каналов живут в канале вечно: объявления старше срока снимаются (TASK-091)."""
    before = datetime.now(UTC) - timedelta(days=TelegramSettings.MAX_AGE_DAYS)
    async with db.session_factory() as session:
        archived = await ListingsRepository(session).archive_published_before(TELEGRAM, before)
        await session.commit()
    if archived:
        logger.info("Old Telegram posts archived", count=archived)


async def translate(limit: int) -> TranslationStats:
    """Переводит до ``limit`` объявлений на недостающие языки (ru, ka, en).

    Одновременно работает только один перевод (advisory lock в PostgreSQL): иначе
    два процесса переводят одни и те же объявления (двойная оплата AI) и ловят deadlock.

    Raises:
        TranslationBusyError: перевод уже запущен в другом процессе.
    """
    db = DatabaseManager()
    checked = translated = failed = unavailable = 0
    error = ""
    try:
        async with advisory_lock(db.engine, TRANSLATE_LOCK) as acquired:
            if not acquired:
                raise TranslationBusyError("translation is already running")
            # Сначала текст не на своём языке (русский в грузинской колонке) — на место:
            # освободившиеся языки переведутся ниже в этом же запуске
            async with db.session_factory() as session:
                fixed = await ListingsRepository(session).fix_wrong_languages(LANGUAGE_FIX_BATCH)
                await session.commit()
            if fixed:
                logger.info("Texts in a wrong language fixed", listings=fixed)
            provider = LLMFactory.create_provider()
            try:
                while checked < limit:
                    async with db.session_factory() as session:
                        use_case = TranslateListingsUseCase(
                            LLMTranslator(provider),
                            ListingsRepository(session),
                            after_save=session.commit,
                            concurrency=LLM_CONCURRENCY,
                        )
                        stats = await use_case.execute(min(TRANSLATE_BATCH, limit - checked))
                        await session.commit()
                    checked += stats.checked
                    translated += stats.translated
                    failed += stats.failed
                    unavailable += stats.unavailable
                    error = stats.error or error
                    # Больше нечего переводить или вся пачка не перевелась (не крутим одни и те же)
                    if stats.checked == 0 or stats.translated == 0:
                        break
            finally:
                close = getattr(provider, "close", None)
                if close is not None:
                    await close()
    finally:
        await db.dispose()
    if unavailable and not translated:
        # Шаг «translate» в расписании упадёт — владелец получит сообщение в Telegram
        raise TranslatorDownError(error)
    return TranslationStats(
        checked=checked,
        translated=translated,
        failed=failed,
        unavailable=unavailable,
        error=error,
    )


class TranslatorDownError(RuntimeError):
    """AI не отвечает: перевод не идёт (баланс, ключ, связь)."""


BUSY_MESSAGE = (
    "перевод уже идёт в другом процессе (сервис scraper переводит сам после парсинга), "
    "попробуйте через несколько минут"
)


class FraudCheckBusyError(RuntimeError):
    """Проверка на мошенничество уже идёт в другом процессе."""


FRAUD_BUSY_MESSAGE = (
    "проверка на мошенничество уже идёт в другом процессе, попробуйте через несколько минут"
)


async def check_fraud(limit: int) -> FraudStats:
    """Проверяет до ``limit`` объявлений на мошенничество (правила + AI).

    Одновременно — только одна проверка (advisory lock), как и перевод.

    Raises:
        FraudCheckBusyError: проверка уже запущена в другом процессе.
    """
    db = DatabaseManager()
    checked = suspicious = hidden = failed = 0
    try:
        async with advisory_lock(db.engine, FRAUD_LOCK) as acquired:
            if not acquired:
                raise FraudCheckBusyError("fraud check is already running")
            provider = LLMFactory.create_provider()
            try:
                while checked + failed < limit:
                    async with db.session_factory() as session:
                        use_case = CheckFraudUseCase(
                            LLMFraudAnalyzer(provider),
                            ListingsRepository(session),
                            after_save=session.commit,
                            concurrency=LLM_CONCURRENCY,
                        )
                        stats = await use_case.execute(
                            min(TRANSLATE_BATCH, limit - checked - failed)
                        )
                        await session.commit()
                    checked += stats.checked
                    suspicious += stats.suspicious
                    hidden += stats.hidden
                    failed += stats.failed
                    # Больше нечего проверять или вся пачка не прошла (не крутим одни и те же)
                    if stats.checked == 0:
                        break
            finally:
                close = getattr(provider, "close", None)
                if close is not None:
                    await close()
    finally:
        await db.dispose()
    return FraudStats(checked=checked, suspicious=suspicious, hidden=hidden, failed=failed)


async def fill_details(limit: int, recheck_days: int = 0) -> BackfillStats:
    """Открывает страницы до ``limit`` объявлений: без подробностей и давно не виденных.

    ``recheck_days``: через сколько дней без появления в списке сайта объявление
    проверяется заново (снятое уходит в архив); 0 — не проверять.
    """
    recheck_before = datetime.now(UTC) - timedelta(days=recheck_days) if recheck_days else None
    db = DatabaseManager()
    scrapers = {source: make_scraper(source, details=True, dump_dir=None) for source in SOURCES}
    try:
        return await backfill_details(
            db.session_factory,
            {source: cast(DetailsSource, scraper) for source, scraper in scrapers.items()},
            limit,
            recheck_before,
        )
    finally:
        for scraper in scrapers.values():
            close = getattr(scraper, "close", None)
            if close is not None:
                await close()
        await db.dispose()


def _echo_details(stats: BackfillStats) -> None:
    click.echo(
        f"подробности: проверено {stats.checked}, обновлено {stats.updated}, "
        f"снято с сайта {stats.archived}, ошибок {stats.failed}"
    )


def _echo_fraud(stats: FraudStats) -> None:
    click.echo(
        f"антифрод: проверено {stats.checked}, подозрительных {stats.suspicious}, "
        f"скрыто {stats.hidden}, ошибок {stats.failed}"
    )


def _echo_translation(stats: TranslationStats) -> None:
    click.echo(
        f"перевод: проверено {stats.checked}, переведено {stats.translated}, ошибок {stats.failed}"
    )


async def find_duplicates(limit: int) -> DuplicateStats:
    """Ищет ту же квартиру на разных сайтах среди ещё не проверенных объявлений (TASK-090)."""
    db = DatabaseManager()
    try:
        async with db.session_factory() as session:
            stats = await FindDuplicatesUseCase(ListingsRepository(session)).execute(limit)
            await session.commit()
        return stats
    finally:
        await db.dispose()


def _echo_duplicates(stats: DuplicateStats) -> None:
    click.echo(f"дубликаты: проверено {stats.checked}, склеено {stats.found}")


async def geocode(limit: int) -> GeocodeStats:
    """Ищет на карте адреса объявлений без координат (Telegram-каналы, TASK-080)."""
    from bina.infrastructure.geo.nominatim import NominatimGeocoder

    db = DatabaseManager()
    geocoder = NominatimGeocoder()
    try:
        async with db.session_factory() as session:
            stats = await GeocodeListingsUseCase(ListingsRepository(session), geocoder).execute(
                limit
            )
            await session.commit()
        return stats
    finally:
        await geocoder.close()
        await db.dispose()


async def embed(limit: int) -> EmbedStats:
    """Отпечатки смысла для умного поиска (TASK-012)."""
    from bina.infrastructure.db.repositories.embeddings import EmbeddingsRepository

    db = DatabaseManager()
    embedder = LLMFactory.create_embeddings_provider()
    try:
        async with db.session_factory() as session:
            stats = await EmbedListingsUseCase(EmbeddingsRepository(session), embedder).execute(
                limit
            )
            await session.commit()
        return stats
    finally:
        await embedder.close()
        await db.dispose()


def _echo_embed(stats: EmbedStats) -> None:
    click.echo(
        f"умный поиск: объявлений {stats.checked}, отпечатков {stats.embedded}, "
        f"отложено {stats.failed}"
    )


# TASK-114: сколько объявлений разбирать по фото за запуск (PHOTO_ANALYSIS_LIMIT, 0 — выключено)
DEFAULT_PHOTO_LIMIT = 50


def photo_limit() -> int:
    raw = os.getenv("PHOTO_ANALYSIS_LIMIT", "").strip()
    try:
        return max(int(raw), 0) if raw else DEFAULT_PHOTO_LIMIT
    except ValueError:
        return DEFAULT_PHOTO_LIMIT


async def analyze_photos(limit: int) -> PhotoStats:
    """AI-разбор фото новых объявлений: ремонт и видимые дефекты (TASK-114)."""
    db = DatabaseManager()
    analyzer = create_photo_analyzer()
    try:
        async with db.session_factory() as session:
            use_case = AnalyzePhotosUseCase(
                PhotoReportsRepository(session),
                analyzer,
                model=analyzer.model,
                after_save=session.commit,
            )
            stats = await use_case.execute(limit)
            await session.commit()
        return stats
    finally:
        await analyzer.close()
        await db.dispose()


async def bump_listings() -> int:
    """Поднять Premium-объявления агентств, у которых подошло время (TASK-100)."""
    db = DatabaseManager()
    try:
        async with db.session_factory() as session:
            bumped = await run_bumps(AgenciesRepository(session), datetime.now(UTC))
            await session.commit()
        return bumped
    finally:
        await db.dispose()


def _echo_report(sent: bool) -> None:
    if sent:
        click.echo("Ежедневный отчёт отправлен владельцу")


def _echo_bumps(bumped: int) -> None:
    click.echo(f"premium-объявления: поднято {bumped}")


def _echo_photos(stats: PhotoStats) -> None:
    click.echo(f"фото: разобрано объявлений {stats.analyzed}, отложено {stats.failed}")


def _echo_geocode(stats: GeocodeStats) -> None:
    click.echo(
        f"карта: проверено адресов {stats.checked}, на карте {stats.found}, ошибок {stats.failed}"
    )


async def premium_reminders() -> PremiumReminderStats:
    """Напоминания об окончании Premium (TASK-107); отправит их ``notify``."""
    from bina.infrastructure.db.repositories.premium_reminders import (
        PremiumRemindersRepository,
    )

    db = DatabaseManager()
    try:
        async with db.session_factory() as session:
            stats = await PremiumRemindersUseCase(PremiumRemindersRepository(session)).execute(
                datetime.now(UTC)
            )
            await session.commit()
        return stats
    finally:
        await db.dispose()


def _echo_premium(stats: PremiumReminderStats) -> None:
    click.echo(f"premium: напоминаний {stats.reminded}, «закончился» {stats.expired}")


async def rent_reminders() -> RentReminderStats | None:
    """Напоминания об оплате аренды (TASK-109); ``None`` — нет ``BOT_TOKEN``."""
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        return None
    from aiogram import Bot

    from bina.infrastructure.bot.rent_reminders import TelegramRentReminderSender
    from bina.infrastructure.db.repositories.rent_reminders import RentRemindersRepository

    db = DatabaseManager()
    bot = Bot(token=token, default=_bot_defaults())
    try:
        async with db.session_factory() as session:
            stats = await SendRentRemindersUseCase(
                RentRemindersRepository(session), TelegramRentReminderSender(bot)
            ).execute(datetime.now(UTC))
            await session.commit()
        return stats
    finally:
        await bot.session.close()
        await db.dispose()


def _echo_rent(stats: RentReminderStats | None) -> None:
    if stats is None:
        click.echo("аренда: напоминания не отправлены (нет BOT_TOKEN)")
    else:
        click.echo(f"аренда: напоминаний отправлено {stats.sent}, ошибок {stats.failed}")


async def notify() -> tuple[CreatedNotifications, DeliveryStats | None]:
    """Создаёт уведомления и отправляет их в Telegram (если задан ``BOT_TOKEN``)."""
    db = DatabaseManager()
    try:
        async with db.session_factory() as session:
            created = await CreateNotificationsUseCase(
                SavedSearchesRepository(session),
                ListingsRepository(session),
                NotificationsRepository(session),
            ).execute()
            await session.commit()

        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            logger.warning("BOT_TOKEN is not set: notifications are not sent to Telegram")
            return created, None

        # Импорт здесь: парсеру без уведомлений aiogram не нужен
        from aiogram import Bot

        from bina.infrastructure.bot.notifications import TelegramNotificationSender

        bot = Bot(token=token, default=_bot_defaults())
        sender = TelegramNotificationSender(bot, os.getenv("BOT_MINI_APP_URL", "").strip() or None)
        sent = skipped = failed = 0
        try:
            while True:
                async with db.session_factory() as session:
                    stats = await DeliverNotificationsUseCase(
                        NotificationsRepository(session),
                        sender,
                        free_delay=timedelta(hours=ScraperSettings.FREE_ALERT_DELAY_HOURS),
                    ).execute(limit=DELIVERY_BATCH)
                    await session.commit()
                sent += stats.sent
                skipped += stats.skipped
                failed += stats.failed
                # Очередь пуста или остались только временные ошибки — до следующего запуска
                if stats.sent + stats.skipped == 0:
                    break
        finally:
            await bot.session.close()
        return created, DeliveryStats(sent=sent, skipped=skipped, failed=failed)
    finally:
        await db.dispose()


def _bot_defaults() -> "DefaultBotProperties":
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    return DefaultBotProperties(parse_mode=ParseMode.HTML)


def _echo_notifications(created: CreatedNotifications, delivery: DeliveryStats | None) -> None:
    line = f"уведомления: новых квартир {created.new_listings}, снижений цены {created.price_drops}"
    if delivery is None:
        line += "; в Telegram не отправлены (нет BOT_TOKEN)"
    else:
        line += (
            f"; отправлено {delivery.sent}, пропущено {delivery.skipped}, ошибок {delivery.failed}"
        )
    click.echo(line)


@cli.command(name="notify")
def notify_command() -> None:
    """Создать уведомления по сохранённым поискам и избранному и отправить их в Telegram."""
    _echo_notifications(*asyncio.run(notify()))


@cli.command(name="translate")
@click.option("--limit", default=50, show_default=True, type=click.IntRange(1, 5000))
def translate_command(limit: int) -> None:
    """Перевести объявления на недостающие языки через AI (нужен LLM_API_KEY)."""
    if not llm_configured():
        raise click.ClickException(
            'Не задан LLM_API_KEY (ключ AITUNNEL). Пример: $env:LLM_API_KEY="..."'
        )
    try:
        _echo_translation(asyncio.run(translate(limit)))
    except TranslationBusyError as exc:
        raise click.ClickException(BUSY_MESSAGE) from exc
    except TranslatorDownError as exc:
        raise click.ClickException(str(exc)) from exc


async def language_status() -> tuple[int, int]:
    """(активных объявлений, из них ждут перевода)."""
    db = DatabaseManager()
    try:
        async with db.session_factory() as session:
            return await ListingsRepository(session).language_coverage()
    finally:
        await db.dispose()


@cli.command(name="languages")
def languages_command() -> None:
    """Сколько объявлений уже на всех трёх языках (ka, ru, en) и сколько ждут перевода."""
    total, missing = asyncio.run(language_status())
    click.echo(
        f"языки: объявлений {total}, на всех трёх языках {total - missing}, ждут перевода {missing}"
    )
    if missing:
        click.echo("перевести: bina-scrape translate --limit 5000")


RECHECK_OPTION = click.option(
    "--recheck-days",
    default=ScraperSettings.RECHECK_DAYS,
    show_default=True,
    type=click.IntRange(0, 365),
    help="Заново проверять объявления, которых столько дней не было в списке сайта (0 — нет).",
)


@cli.command(name="details")
@click.option("--limit", default=100, show_default=True, type=click.IntRange(1, 5000))
@RECHECK_OPTION
def details_command(limit: int, recheck_days: int) -> None:
    """Дозагрузить подробности и проверить, не сняты ли старые объявления с сайта."""
    _echo_details(asyncio.run(fill_details(limit, recheck_days)))


async def source_stats() -> list[tuple[str, str, int]]:
    """Сколько объявлений у каждого источника: в поиске и снятых."""
    db = DatabaseManager()
    try:
        async with db.session_factory() as session:
            return await ListingsRepository(session).source_stats()
    finally:
        await db.dispose()


_STATUS_NAMES = {"active": "в поиске", "archived": "снято", "sold": "сдано"}


@cli.command(name="stats")
def stats_command() -> None:
    """Сколько объявлений у каждого источника: в поиске и снятых (неактуальных)."""
    rows = asyncio.run(source_stats())
    if not rows:
        click.echo("объявлений пока нет")
        return
    for source in dict.fromkeys(row[0] for row in rows):
        parts = [
            f"{_STATUS_NAMES.get(status, status)} {count}"
            for name, status, count in rows
            if name == source
        ]
        click.echo(f"{source}: " + ", ".join(parts))


@cli.command(name="duplicates")
@click.option("--limit", default=5000, show_default=True, type=click.IntRange(1, 100000))
def duplicates_command(limit: int) -> None:
    """Найти одну и ту же квартиру на разных сайтах и показывать её один раз."""
    _echo_duplicates(asyncio.run(find_duplicates(limit)))


@cli.command(name="geocode")
@click.option("--limit", default=GEOCODE_BATCH, show_default=True, type=click.IntRange(1, 1000))
def geocode_command(limit: int) -> None:
    """Найти на карте объявления без координат по адресу (OpenStreetMap)."""
    _echo_geocode(asyncio.run(geocode(limit)))


@cli.command(name="photos")
@click.option(
    "--limit", default=DEFAULT_PHOTO_LIMIT, show_default=True, type=click.IntRange(1, 5000)
)
def photos_command(limit: int) -> None:
    """AI-разбор фото объявлений: ремонт и дефекты (ключ — LLM_API_KEY)."""
    if not photo_analysis_configured():
        raise click.UsageError("Нужен LLM_API_KEY")
    _echo_photos(asyncio.run(analyze_photos(limit)))


@cli.command(name="embeddings")
@click.option("--limit", default=EMBED_BATCH, show_default=True, type=click.IntRange(1, 20000))
def embeddings_command(limit: int) -> None:
    """Посчитать отпечатки смысла для умного поиска (ключ — EMBEDDINGS_API_KEY или LLM_API_KEY)."""
    if not embeddings_configured():
        raise click.UsageError("Нужен EMBEDDINGS_API_KEY или LLM_API_KEY")
    try:
        _echo_embed(asyncio.run(embed(limit)))
    except EmbeddingsError as exc:
        raise click.ClickException(f"Сервис AI не посчитал отпечатки: {exc}") from exc


@cli.command(name="rent-reminders")
def rent_reminders_command() -> None:
    """Отправить напоминания об оплате аренды (за 3 дня, за 1 день и в день оплаты)."""
    _echo_rent(asyncio.run(rent_reminders()))


@cli.command(name="premium-reminders")
def premium_reminders_command() -> None:
    """Напомнить об окончании Premium (за 3 дня и после) — отправит `bina-scrape notify`."""
    _echo_premium(asyncio.run(premium_reminders()))


@cli.command(name="daily-report")
def daily_report_command() -> None:
    """Прислать ежедневный отчёт владельцу прямо сейчас (TASK-041)."""
    if not asyncio.run(daily_report(datetime.now(UTC), force=True)):
        raise click.ClickException("Не задан BOT_TOKEN или ADMIN_TELEGRAM_IDS")
    click.echo("Отчёт отправлен")


@cli.command(name="fraud")
@click.option("--limit", default=50, show_default=True, type=click.IntRange(1, 5000))
def fraud_command(limit: int) -> None:
    """Проверить новые объявления на мошенничество (правила + AI, нужен LLM_API_KEY)."""
    if not llm_configured():
        raise click.ClickException(
            'Не задан LLM_API_KEY (ключ AITUNNEL). Пример: $env:LLM_API_KEY="..."'
        )
    try:
        _echo_fraud(asyncio.run(check_fraud(limit)))
    except FraudCheckBusyError as exc:
        raise click.ClickException(FRAUD_BUSY_MESSAGE) from exc


@cli.command()
@click.option(
    "--interval",
    default=ScraperSettings.SCRAPE_INTERVAL_HOURS,
    show_default=True,
    type=click.IntRange(1, 168),
    help="Интервал в часах.",
)
@click.option("--limit", default=500, show_default=True, type=click.IntRange(1, 1000))
@click.option(
    "--translate/--no-translate",
    "with_translation",
    default=True,
    show_default=True,
    help="После парсинга переводить новые объявления (если задан LLM_API_KEY).",
)
@click.option(
    "--translate-limit",
    # С livo/korter и посуточной арендой новых объявлений в час больше: 200 не успевали.
    # Переводятся только описания (заголовки собираются сами), это недорого
    default=1000,
    show_default=True,
    type=click.IntRange(1, 5000),
    help="Максимум объявлений для перевода за запуск.",
)
@click.option(
    "--details-limit",
    default=50,
    show_default=True,
    type=click.IntRange(0, 5000),
    help="Сколько старых объявлений дозагрузить и перепроверить за запуск (0 — не надо).",
)
@RECHECK_OPTION
@click.option(
    "--fraud-limit",
    default=200,
    show_default=True,
    type=click.IntRange(1, 5000),
    help="Максимум объявлений для проверки на мошенничество за запуск (с --translate).",
)
def schedule(
    interval: int,
    limit: int,
    with_translation: bool,
    translate_limit: int,
    details_limit: int,
    recheck_days: int,
    fraud_limit: int,
) -> None:
    """Парсить все источники по расписанию (первый запуск сразу, Ctrl+C: стоп)."""
    if with_translation and not llm_configured():
        click.echo("LLM_API_KEY не задан: перевод отключён, только парсинг.")
        with_translation = False

    monitor = HealthMonitor()

    async def step(name: str, action: Callable[[], Awaitable[None]]) -> None:
        """Шаг запуска: сбой не останавливает расписание, но о нём узнает владелец."""
        try:
            await action()
        except (TranslationBusyError, FraudCheckBusyError):
            raise
        except Exception as exc:  # noqa: BLE001 - ошибка шага не останавливает расписание
            logger.error("Scheduled step failed", step=name, error=str(exc))
            monitor.step_failed(name, str(exc) or type(exc).__name__, datetime.now(UTC))
        else:
            monitor.step_ok(name)

    async def scrape_step() -> None:
        results = await scrape(scrape_sources(), limit)
        click.echo(
            f"[{datetime.now():%Y-%m-%d %H:%M}] парсинг завершён, следующий через {interval} ч"
        )
        _echo_results(results)
        for result in results:
            monitor.source_result(result.source, result.scraped, datetime.now(UTC))

    async def translate_step() -> None:
        try:
            _echo_translation(await translate(translate_limit))
        except TranslationBusyError:
            click.echo(BUSY_MESSAGE)

    async def fraud_step() -> None:
        try:
            _echo_fraud(await check_fraud(fraud_limit))
        except FraudCheckBusyError:
            click.echo(FRAUD_BUSY_MESSAGE)

    async def job() -> None:
        await step("scrape", scrape_step)
        if details_limit:
            await step(
                "details",
                lambda: _echo_async(_echo_details, fill_details(details_limit, recheck_days)),
            )
        # До перевода: скрытые дубликаты не переводятся (экономия AI)
        await step(
            "duplicates", lambda: _echo_async(_echo_duplicates, find_duplicates(DUPLICATES_BATCH))
        )
        await step("geocode", lambda: _echo_async(_echo_geocode, geocode(GEOCODE_BATCH)))
        if with_translation:
            await step("translate", translate_step)
            # До уведомлений: подозрительные объявления не должны в них попасть
            await step("fraud", fraud_step)
            # TASK-114: ремонт и дефекты по фото (до уведомлений — значок уже в них)
            if photo_limit():
                await step(
                    "photos", lambda: _echo_async(_echo_photos, analyze_photos(photo_limit()))
                )
        # После перевода: в отпечаток идёт английский текст (TASK-012)
        if embeddings_configured():
            await step("embeddings", lambda: _echo_async(_echo_embed, embed(EMBED_BATCH)))
        # TASK-100: до уведомлений — поднятые объявления уже наверху
        await step("bumps", lambda: _echo_async(_echo_bumps, bump_listings()))
        await step("rent", lambda: _echo_async(_echo_rent, rent_reminders()))
        await step("premium", lambda: _echo_async(_echo_premium, premium_reminders()))
        await step("notify", notify_step)
        monitor.api_health(await check_api_health(), datetime.now(UTC))
        await send_owner_alerts(monitor.collect())
        # TASK-041: раз в день — сводка владельцу
        await step("report", lambda: _echo_async(_echo_report, daily_report(datetime.now(UTC))))

    async def run() -> None:
        scheduler = ScraperScheduler(job, interval_hours=interval)
        scheduler.start()
        try:
            await asyncio.Event().wait()
        finally:
            await scheduler.stop()

    asyncio.run(run())


async def _echo_async(echo: Callable[[Any], None], result: Awaitable[Any]) -> None:
    echo(await result)


async def notify_step() -> None:
    _echo_notifications(*await notify())


async def check_api_health() -> str | None:
    """Проверить сервер Mini App (``API_HEALTH_URL``); ``None`` — работает или не задано."""
    url = os.getenv("API_HEALTH_URL", "").strip()
    if not url:
        return None
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        return str(exc) or type(exc).__name__
    return None if response.status_code == 200 else f"HTTP {response.status_code}"


async def send_owner_alerts(alerts: list[Alert]) -> None:
    """Написать владельцу (``ADMIN_TELEGRAM_IDS``) в Telegram на его языке."""
    if not alerts:
        return
    from bina.infrastructure.bot.texts import t

    await _send_to_admins(
        lambda language: "\n\n".join(t(language, a.text, **a.params) for a in alerts)
    )


async def daily_report(now: datetime, *, force: bool = False) -> bool:
    """Ежедневный отчёт владельцу (TASK-041): раз в день после ``DAILY_REPORT_HOUR``.

    ``force`` — отправить сейчас, не глядя на час и на то, отправлен ли уже. ``True`` — отправлен.
    """
    if not os.getenv("BOT_TOKEN", "").strip() or not _admin_ids():
        return False
    day = now.astimezone(TBILISI).date() if force else report_day(now)
    if day is None:
        return False
    db = DatabaseManager()
    try:
        async with db.session_factory() as session:
            admin = AdminRepository(session)
            if not force and not await admin.claim_daily_report(day):
                return False
            report = await admin.daily(now)
            await session.commit()
    finally:
        await db.dispose()
    await _send_to_admins(lambda language: render_daily_report(language, day, report))
    return True


def render_daily_report(language: str, day: date, report: DailyReport) -> str:
    from bina.infrastructure.bot.texts import t

    return t(
        language,
        "daily_report",
        day=f"{day:%d.%m.%Y}",
        users=report.users,
        users_new=report.users_new,
        listings=report.listings,
        listings_new=report.listings_new,
        owner_listings_new=report.owner_listings_new,
        agencies=report.agencies,
        agencies_new=report.agencies_new,
        chats_new=report.chats_new,
        viewings_new=report.viewings_new,
        payments=report.payments,
        stars=f"{report.stars:.0f}",
        premium=report.premium,
        ai_requests=report.ai_requests,
        complaints=report.open_complaints,
        verifications=report.verifications_pending,
    )


async def _send_to_admins(render: Callable[[str], str]) -> None:
    """Отправить каждому админу текст на его языке; сбой отправки не роняет расписание."""
    token = os.getenv("BOT_TOKEN", "").strip()
    admin_ids = _admin_ids()
    if not token or not admin_ids:
        return
    from aiogram import Bot

    db = DatabaseManager()
    bot = Bot(token=token, default=_bot_defaults())
    try:
        async with db.session_factory() as session:
            languages = await UsersRepository(session).languages_by_telegram_ids(admin_ids)
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    admin_id, render(languages.get(admin_id, "ru")), parse_mode=None
                )
            except Exception as exc:  # noqa: BLE001 - сообщение владельцу не должно ронять расписание
                logger.warning("Owner message not sent", admin_id=admin_id, error=str(exc))
    finally:
        await bot.session.close()
        await db.dispose()


def _admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_TELEGRAM_IDS", "").replace(" ", "")
    return [int(part) for part in raw.split(",") if part.isdigit()]


def _echo_results(results: list[ScrapeResult]) -> None:
    """Итог по каждому источнику."""
    for result in results:
        click.echo(
            f"{result.source}: найдено {result.scraped}, прошло проверку {result.valid}, "
            f"новых или изменённых {result.changed}, сохранено {result.saved}"
        )
        if not result.scraped:
            click.echo(
                f"ВНИМАНИЕ: {result.source} не дал ни одного объявления — "
                "сайт недоступен или изменился (нужна проверка парсера)"
            )


def main() -> None:
    """Точка входа ``bina-scrape``."""
    cli()


if __name__ == "__main__":
    main()
