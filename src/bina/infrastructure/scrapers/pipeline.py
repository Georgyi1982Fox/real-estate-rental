"""Полный цикл парсинга: источник → нормализация → дедупликация → БД."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import BaseScraper, RawListing
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.llm.llm_factory import LLMFactory
from bina.infrastructure.scrapers.deduplicator import (
    KnownListing,
    ListingDeduplicator,
    needs_details,
)
from bina.infrastructure.scrapers.normalizer import ListingNormalizer
from bina.infrastructure.scrapers.repository import ScrapedListingsRepository

logger = structlog.get_logger(__name__)

# Сколько помнить объявления, из которых не вышло объявления (потом — попробовать снова)
SKIP_REMEMBER = timedelta(days=30)


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
    """Парсит источник и сохраняет новые и изменившиеся объявления (с коммитом).

    Страницы объявлений открываются только для новых и изменившихся: остальные
    уже есть в базе, для них достаточно отметки «видели на сайте».
    """
    normalizer = ListingNormalizer()
    async with session_factory() as session:
        repository = ListingsRepository(session)
        rows = await repository.source_snapshot(source)
        skipped = await repository.recent_skips(source, datetime.now(UTC) - SKIP_REMEMBER)
    known = {row.source_id: KnownListing(*row[1:]) for row in rows}
    opened: set[str] = set()

    async def fresh(card: RawListing) -> bool:
        if card.source_id in skipped:
            # Уже разбирали: не аренда, другой город или не хватает данных
            return False
        price, _ = normalizer.normalize_price(card.price, card.currency)
        if needs_details(known.get(card.source_id), card, price):
            opened.add(card.source_id)
            return True
        return False

    raw_listings = await scraper.scrape_listings(limit, fresh)
    if not raw_listings:
        # Сайт недоступен или сменил вёрстку: разбор ничего не нашёл
        logger.warning("Scrape found no listings", source=source)
    valid = [n for item in raw_listings if (n := normalizer.normalize_listing(item)) is not None]
    valid_ids = {item.source_id for item in valid}
    # Открыли (для Telegram — разобрали AI), но объявления не вышло: не открывать снова
    rejected = [
        item.source_id
        for item in raw_listings
        if item.source_id in opened and item.source_id not in valid_ids
    ]

    async with session_factory() as session:
        repository = ListingsRepository(session)
        changed = await ListingDeduplicator(repository).deduplicate(valid)
        saved = await ScrapedListingsRepository(session, llm_factory).save_listings(changed)
        await repository.mark_checked(source, [item.source_id for item in raw_listings])
        await repository.add_skips(source, rejected)
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
