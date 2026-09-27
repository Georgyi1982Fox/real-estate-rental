"""Полный цикл парсинга: источник → нормализация → дедупликация → БД."""

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import BaseScraper
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.llm.llm_factory import LLMFactory
from bina.infrastructure.scrapers.deduplicator import ListingDeduplicator
from bina.infrastructure.scrapers.normalizer import ListingNormalizer
from bina.infrastructure.scrapers.repository import ScrapedListingsRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ScrapeResult:
    """Итог парсинга одного источника."""

    source: str
    scraped: int
    valid: int
    changed: int
    saved: int


async def run_scrape(
    scraper: BaseScraper,
    source: str,
    limit: int,
    session_factory: async_sessionmaker[AsyncSession],
    llm_factory: LLMFactory | None = None,
) -> ScrapeResult:
    """Парсит источник и сохраняет новые и изменившиеся объявления (с коммитом)."""
    raw_listings = await scraper.scrape_listings(limit)
    normalizer = ListingNormalizer()
    valid = [n for item in raw_listings if (n := normalizer.normalize_listing(item)) is not None]

    async with session_factory() as session:
        changed = await ListingDeduplicator(ListingsRepository(session)).deduplicate(valid)
        saved = await ScrapedListingsRepository(session, llm_factory).save_listings(changed)
        await session.commit()

    result = ScrapeResult(source, len(raw_listings), len(valid), len(changed), saved)
    logger.info(
        "Scrape finished",
        source=source,
        scraped=result.scraped,
        valid=result.valid,
        changed=result.changed,
        saved=result.saved,
    )
    return result
