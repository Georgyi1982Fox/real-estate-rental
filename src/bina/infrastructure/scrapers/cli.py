import asyncio
import os

import click
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.llm.llm_factory import LLMFactory
from bina.infrastructure.scrapers.deduplicator import ListingDeduplicator
from bina.infrastructure.scrapers.myhome_scraper import MyHomeScraper
from bina.infrastructure.scrapers.normalizer import ListingNormalizer
from bina.infrastructure.scrapers.repository import ScrapedListingsRepository
from bina.infrastructure.scrapers.scheduler import ScraperScheduler
from bina.infrastructure.scrapers.ss_scraper import SSScraper

# Настройка логгирования
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@click.group()
def cli():
    """CLI для парсинга объявлений недвижимости."""
    pass


@cli.command()
@click.option("--limit", default=50, help="Количество объявлений для парсинга")
def myhome(limit: int):
    """Парсит объявления с MyHome.ge."""
    asyncio.run(_scrape_myhome(limit))


@cli.command()
@click.option("--limit", default=50, help="Количество объявлений для париснга")
def ss(limit: int):
    """Парсит объявления с SS.ge."""
    asyncio.run(_scrape_ss(limit))


@cli.command()
@click.option("--limit", default=100, help="Количество объявлений для парсинга")
def all(limit: int):
    """Парсит объявления со всех источников."""
    asyncio.run(_scrape_all(limit))


@cli.command()
@click.option("--interval", default=6, help="Интервал в часах")
def schedule(interval: int):
    """Запускает планировщик парсинга."""
    asyncio.run(_run_scheduler(interval))


async def _get_db_session() -> AsyncSession:
    """Создает сессию БД."""
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/bina")
    engine = create_async_engine(database_url, echo=False)
    session = AsyncSession(engine)
    return session


async def _scrape_myhome(limit: int):
    """Парсит MyHome.ge."""
    logger.info("Starting MyHome scraping", limit=limit)

    # Создаем зависимости
    session = await _get_db_session()
    try:
        myhome_scraper = MyHomeScraper(
            delay_seconds=int(os.getenv("SCRAPE_DELAY_SECONDS", "2")),
            user_agents=os.getenv("SCRAPE_USER_AGENTS", "").split(",") if os.getenv("SCRAPE_USER_AGENTS") else None,
        )

        listing_repository = ListingsRepository(session)
        normalizer = ListingNormalizer()
        deduplicator = ListingDeduplicator(listing_repository)
        llm_factory = LLMFactory()
        repository = ScrapedListingsRepository(listing_repository, llm_factory)

        # Парсим
        raw_listings = await myhome_scraper.scrape_listings(limit)
        logger.info("Raw listings scraped", count=len(raw_listings))

        normalized_listings = []
        for listing in raw_listings:
            normalized = normalizer.normalize_listing(listing)
            if normalized:
                normalized_listings.append(normalized)

        unique_listings = await deduplicator.deduplicate(normalized_listings)
        saved_count = await repository.save_listings(unique_listings)

        logger.info("MyHome scraping completed", saved=saved_count)

    finally:
        await session.close()
        await myhome_scraper.close()


async def _scrape_ss(limit: int):
    """Парсит SS.ge."""
    logger.info("Starting SS scraping", limit=limit)

    # Создаем зависимости
    session = await _get_db_session()
    try:
        ss_scraper = SSScraper(
            delay_seconds=int(os.getenv("SCRAPE_DELAY_SECONDS", "2")),
            user_agents=os.getenv("SCRAPE_USER_AGENTS", "").split(",") if os.getenv("SCRAPE_USER_AGENTS") else None,
        )

        listing_repository = ListingsRepository(session)
        normalizer = ListingNormalizer()
        deduplicator = ListingDeduplicator(listing_repository)
        llm_factory = LLMFactory()
        repository = ScrapedListingsRepository(listing_repository, llm_factory)

        # Парсим
        raw_listings = await ss_scraper.scrape_listings(limit)
        logger.info("Raw listings scraped", count=len(raw_listings))

        normalized_listings = []
        for listing in raw_listings:
            normalized = normalizer.normalize_listing(listing)
            if normalized:
                normalized_listings.append(normalized)

        unique_listings = await deduplicator.deduplicate(normalized_listings)
        saved_count = await repository.save_listings(unique_listings)

        logger.info("SS scraping completed", saved=saved_count)

    finally:
        await session.close()
        await ss_scraper.close()


async def _scrape_all(limit: int):
    """Парсит все источники."""
    logger.info("Starting all sources scraping", limit=limit)

    # Создаем зависимости
    session = await _get_db_session()
    try:
        myhome_scraper = MyHomeScraper(
            delay_seconds=int(os.getenv("SCRAPE_DELAY_SECONDS", "2")),
            user_agents=os.getenv("SCRAPE_USER_AGENTS", "").split(",") if os.getenv("SCRAPE_USER_AGENTS") else None,
        )
        ss_scraper = SSScraper(
            delay_seconds=int(os.getenv("SCRAPE_DELAY_SECONDS", "2")),
            user_agents=os.getenv("SCRAPE_USER_AGENTS", "").split(",") if os.getenv("SCRAPE_USER_AGENTS") else None,
        )

        listing_repository = ListingsRepository(session)
        normalizer = ListingNormalizer()
        deduplicator = ListingDeduplicator(listing_repository)
        llm_factory = LLMFactory()
        repository = ScrapedListingsRepository(listing_repository, llm_factory)

        # Парсим MyHome
        myhome_limit = limit // 2
        myhome_listings = await myhome_scraper.scrape_listings(myhome_limit)
        logger.info("MyHome raw listings scraped", count=len(myhome_listings))

        # Парсим SS
        ss_limit = limit - myhome_limit
        ss_listings = await ss_scraper.scrape_listings(ss_limit)
        logger.info("SS raw listings scraped", count=len(ss_listings))

        # Объединяем и обрабатываем
        all_raw_listings = myhome_listings + ss_listings
        normalized_listings = []
        for listing in all_raw_listings:
            normalized = normalizer.normalize_listing(listing)
            if normalized:
                normalized_listings.append(normalized)

        unique_listings = await deduplicator.deduplicate(normalized_listings)
        saved_count = await repository.save_listings(unique_listings)

        logger.info("All sources scraping completed", saved=saved_count)

    finally:
        await session.close()
        await myhome_scraper.close()
        await ss_scraper.close()


async def _run_scheduler(interval: int):
    """Запускает планировщик."""
    logger.info("Starting scraper scheduler", interval_hours=interval)

    # Создаем зависимости
    session = await _get_db_session()
    try:
        myhome_scraper = MyHomeScraper(
            delay_seconds=int(os.getenv("SCRAPE_DELAY_SECONDS", "2")),
            user_agents=os.getenv("SCRAPE_USER_AGENTS", "").split(",") if os.getenv("SCRAPE_USER_AGENTS") else None,
        )
        ss_scraper = SSScraper(
            delay_seconds=int(os.getenv("SCRAPE_DELAY_SECONDS", "2")),
            user_agents=os.getenv("SCRAPE_USER_AGENTS", "").split(",") if os.getenv("SCRAPE_USER_AGENTS") else None,
        )

        listing_repository = ListingsRepository(session)
        normalizer = ListingNormalizer()
        deduplicator = ListingDeduplicator(listing_repository)
        llm_factory = LLMFactory()
        repository = ScrapedListingsRepository(listing_repository, llm_factory)

        scheduler = ScraperScheduler(
            myhome_scraper=myhome_scraper,
            ss_scraper=ss_scraper,
            normalizer=normalizer,
            deduplicator=deduplicator,
            repository=repository,
            interval_hours=interval,
        )

        scheduler.start()

        try:
            # Ждем нажатия Ctrl+C
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user")
        finally:
            await scheduler.stop()

    finally:
        await session.close()


def main():
    """Главная функция CLI."""
    cli()


if __name__ == "__main__":
    main()
