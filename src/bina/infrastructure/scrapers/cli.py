"""CLI парсера: ``bina-scrape --source myhome --limit 100``."""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import click
import structlog

from bina.application.ports.scraper import BaseScraper
from bina.application.use_cases.check_fraud import CheckFraudUseCase, FraudStats
from bina.application.use_cases.notifications import (
    CreatedNotifications,
    CreateNotificationsUseCase,
    DeliverNotificationsUseCase,
    DeliveryStats,
)
from bina.application.use_cases.translate_listings import (
    TranslateListingsUseCase,
    TranslationStats,
)
from bina.infrastructure.db.locks import FRAUD_LOCK, TRANSLATE_LOCK, advisory_lock
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.notifications import (
    NotificationsRepository,
    SavedSearchesRepository,
)
from bina.infrastructure.db.session.manager import DatabaseManager
from bina.infrastructure.llm.fraud_analyzer import LLMFraudAnalyzer
from bina.infrastructure.llm.llm_factory import LLMFactory
from bina.infrastructure.llm.translator import LLMTranslator
from bina.infrastructure.scrapers.myhome_scraper import MyHomeScraper
from bina.infrastructure.scrapers.pipeline import ScrapeResult, run_scrape
from bina.infrastructure.scrapers.scheduler import ScraperScheduler
from bina.infrastructure.scrapers.settings import ScraperSettings
from bina.infrastructure.scrapers.ss_scraper import SSScraper

if TYPE_CHECKING:
    from aiogram.client.default import DefaultBotProperties

logger = structlog.get_logger(__name__)

SOURCES = ("myhome", "ss")
# Перевод коммитится пачками: сбой посередине не теряет уже сделанное
TRANSLATE_BATCH = 10
# Отправка уведомлений пачками (коммит после каждой)
DELIVERY_BATCH = 100


def make_scraper(source: str, *, details: bool, dump_dir: Path | None) -> BaseScraper:
    """Создаёт парсер источника с настройками из окружения."""
    common = {
        "delay_seconds": ScraperSettings.SCRAPE_DELAY_SECONDS,
        "user_agents": ScraperSettings.SCRAPE_USER_AGENTS,
    }
    if source == "myhome":
        return MyHomeScraper(**common, fetch_details=details, dump_dir=dump_dir)  # type: ignore[arg-type]
    if source == "ss":
        return SSScraper(**common, dump_dir=dump_dir)  # type: ignore[arg-type]
    raise click.BadParameter(f"unknown source {source!r}")


async def scrape(
    sources: list[str],
    limit: int,
    *,
    details: bool = True,
    embeddings: bool = False,
    dump_dir: Path | None = None,
) -> list[ScrapeResult]:
    """Парсит источники по очереди и сохраняет результат в БД (``DATABASE_URL``)."""
    db = DatabaseManager()
    results: list[ScrapeResult] = []
    try:
        for source in sources:
            scraper = make_scraper(source, details=details, dump_dir=dump_dir)
            try:
                results.append(
                    await run_scrape(
                        scraper,
                        source,
                        limit,
                        db.session_factory,
                        LLMFactory() if embeddings else None,
                    )
                )
            finally:
                close = getattr(scraper, "close", None)
                if close is not None:
                    await close()
    finally:
        await db.dispose()
    return results


@click.group(invoke_without_command=True)
@click.option(
    "--source",
    type=click.Choice([*SOURCES, "all"]),
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
    "--embeddings/--no-embeddings",
    default=False,
    show_default=True,
    help="Создавать embeddings (нужен ключ LLM API).",
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
    embeddings: bool,
    dump_dir: Path | None,
) -> None:
    """Парсинг объявлений недвижимости (MyHome.ge, SS.ge) в БД.

    Пример: bina-scrape --source myhome --limit 100
    """
    if ctx.invoked_subcommand is not None:
        return
    if source is None:
        raise click.UsageError("Укажите --source (myhome, ss или all)")

    sources = list(SOURCES) if source == "all" else [source]
    results = asyncio.run(
        scrape(sources, limit, details=details, embeddings=embeddings, dump_dir=dump_dir)
    )
    _echo_results(results)


def llm_configured() -> bool:
    """Задан ли ключ AI (``LLM_API_KEY``)."""
    return bool(os.getenv("LLM_API_KEY"))


class TranslationBusyError(RuntimeError):
    """Перевод уже идёт в другом процессе (например, в сервисе ``scraper``)."""


async def translate(limit: int) -> TranslationStats:
    """Переводит до ``limit`` объявлений на недостающие языки (ru, ka, en).

    Одновременно работает только один перевод (advisory lock в PostgreSQL): иначе
    два процесса переводят одни и те же объявления (двойная оплата AI) и ловят deadlock.

    Raises:
        TranslationBusyError: перевод уже запущен в другом процессе.
    """
    db = DatabaseManager()
    checked = translated = failed = 0
    try:
        async with advisory_lock(db.engine, TRANSLATE_LOCK) as acquired:
            if not acquired:
                raise TranslationBusyError("translation is already running")
            provider = LLMFactory.create_provider()
            try:
                while checked < limit:
                    async with db.session_factory() as session:
                        use_case = TranslateListingsUseCase(
                            LLMTranslator(provider),
                            ListingsRepository(session),
                            after_save=session.commit,
                        )
                        stats = await use_case.execute(min(TRANSLATE_BATCH, limit - checked))
                        await session.commit()
                    checked += stats.checked
                    translated += stats.translated
                    failed += stats.failed
                    # Больше нечего переводить или вся пачка не перевелась (не крутим одни и те же)
                    if stats.checked == 0 or stats.translated == 0:
                        break
            finally:
                close = getattr(provider, "close", None)
                if close is not None:
                    await close()
    finally:
        await db.dispose()
    return TranslationStats(checked=checked, translated=translated, failed=failed)


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


def _echo_fraud(stats: FraudStats) -> None:
    click.echo(
        f"антифрод: проверено {stats.checked}, подозрительных {stats.suspicious}, "
        f"скрыто {stats.hidden}, ошибок {stats.failed}"
    )


def _echo_translation(stats: TranslationStats) -> None:
    click.echo(
        f"перевод: проверено {stats.checked}, переведено {stats.translated}, ошибок {stats.failed}"
    )


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
                        NotificationsRepository(session), sender
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
@click.option("--limit", default=100, show_default=True, type=click.IntRange(1, 1000))
@click.option(
    "--translate/--no-translate",
    "with_translation",
    default=True,
    show_default=True,
    help="После парсинга переводить новые объявления (если задан LLM_API_KEY).",
)
@click.option(
    "--translate-limit",
    default=200,
    show_default=True,
    type=click.IntRange(1, 5000),
    help="Максимум объявлений для перевода за запуск.",
)
@click.option(
    "--fraud-limit",
    default=200,
    show_default=True,
    type=click.IntRange(1, 5000),
    help="Максимум объявлений для проверки на мошенничество за запуск (с --translate).",
)
def schedule(
    interval: int, limit: int, with_translation: bool, translate_limit: int, fraud_limit: int
) -> None:
    """Парсить все источники по расписанию (первый запуск сразу, Ctrl+C: стоп)."""
    if with_translation and not llm_configured():
        click.echo("LLM_API_KEY не задан: перевод отключён, только парсинг.")
        with_translation = False

    async def job() -> None:
        try:
            results = await scrape(list(SOURCES), limit)
            click.echo(
                f"[{datetime.now():%Y-%m-%d %H:%M}] парсинг завершён, следующий через {interval} ч"
            )
            _echo_results(results)
        except Exception as exc:  # noqa: BLE001 - ошибка одного запуска не останавливает расписание
            logger.error("Scheduled scrape failed", error=str(exc))
        if with_translation:
            try:
                _echo_translation(await translate(translate_limit))
            except TranslationBusyError:
                click.echo(BUSY_MESSAGE)
            except Exception as exc:  # noqa: BLE001 - сбой перевода не останавливает расписание
                logger.error("Scheduled translation failed", error=str(exc))
            # До уведомлений: подозрительные объявления не должны в них попасть
            try:
                _echo_fraud(await check_fraud(fraud_limit))
            except FraudCheckBusyError:
                click.echo(FRAUD_BUSY_MESSAGE)
            except Exception as exc:  # noqa: BLE001 - сбой проверки не останавливает расписание
                logger.error("Scheduled fraud check failed", error=str(exc))
        try:
            _echo_notifications(*await notify())
        except Exception as exc:  # noqa: BLE001 - сбой уведомлений не останавливает расписание
            logger.error("Scheduled notifications failed", error=str(exc))

    async def run() -> None:
        scheduler = ScraperScheduler(job, interval_hours=interval)
        scheduler.start()
        try:
            await asyncio.Event().wait()
        finally:
            await scheduler.stop()

    asyncio.run(run())


def _echo_results(results: list[ScrapeResult]) -> None:
    """Итог по каждому источнику."""
    for result in results:
        click.echo(
            f"{result.source}: найдено {result.scraped}, прошло проверку {result.valid}, "
            f"новых или изменённых {result.changed}, сохранено {result.saved}"
        )


def main() -> None:
    """Точка входа ``bina-scrape``."""
    cli()


if __name__ == "__main__":
    main()
