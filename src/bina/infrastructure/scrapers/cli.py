"""CLI парсера: ``bina-scrape --source myhome --limit 100``."""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import click
import structlog

from bina.application.ports.scraper import BaseScraper
from bina.application.use_cases.translate_listings import (
    TranslateListingsUseCase,
    TranslationStats,
)
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.session.manager import DatabaseManager
from bina.infrastructure.llm.llm_factory import LLMFactory
from bina.infrastructure.llm.translator import LLMTranslator
from bina.infrastructure.scrapers.myhome_scraper import MyHomeScraper
from bina.infrastructure.scrapers.pipeline import ScrapeResult, run_scrape
from bina.infrastructure.scrapers.scheduler import ScraperScheduler
from bina.infrastructure.scrapers.settings import ScraperSettings
from bina.infrastructure.scrapers.ss_scraper import SSScraper

logger = structlog.get_logger(__name__)

SOURCES = ("myhome", "ss")
# Перевод коммитится пачками: сбой посередине не теряет уже сделанное
TRANSLATE_BATCH = 10


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


async def translate(limit: int) -> TranslationStats:
    """Переводит до ``limit`` объявлений на недостающие языки (ru, ka, en)."""
    provider = LLMFactory.create_provider()
    db = DatabaseManager()
    checked = translated = failed = 0
    try:
        while checked < limit:
            async with db.session_factory() as session:
                use_case = TranslateListingsUseCase(
                    LLMTranslator(provider), ListingsRepository(session)
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
        await db.dispose()
    return TranslationStats(checked=checked, translated=translated, failed=failed)


def _echo_translation(stats: TranslationStats) -> None:
    click.echo(
        f"перевод: проверено {stats.checked}, переведено {stats.translated}, ошибок {stats.failed}"
    )


@cli.command(name="translate")
@click.option("--limit", default=50, show_default=True, type=click.IntRange(1, 5000))
def translate_command(limit: int) -> None:
    """Перевести объявления на недостающие языки через AI (нужен LLM_API_KEY)."""
    if not llm_configured():
        raise click.ClickException(
            'Не задан LLM_API_KEY (ключ AITUNNEL). Пример: $env:LLM_API_KEY="..."'
        )
    _echo_translation(asyncio.run(translate(limit)))


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
def schedule(interval: int, limit: int, with_translation: bool, translate_limit: int) -> None:
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
        if not with_translation:
            return
        try:
            _echo_translation(await translate(translate_limit))
        except Exception as exc:  # noqa: BLE001 - сбой перевода не останавливает расписание
            logger.error("Scheduled translation failed", error=str(exc))

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
