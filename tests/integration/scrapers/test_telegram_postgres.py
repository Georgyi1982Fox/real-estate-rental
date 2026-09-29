"""Посты Telegram-каналов до базы (TASK-091) на настоящем PostgreSQL."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.listing_extractor import ExtractedListing, IListingExtractor
from bina.infrastructure.db.models import Listing, ListingStatus, ScrapeSkip
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.scrapers.pipeline import run_scrape
from bina.infrastructure.scrapers.telegram_scraper import TelegramChannelScraper

CHANNEL_HTML = Path("tests/unit/infrastructure/scrapers/test_data/tg_channel.html").read_text(
    encoding="utf-8"
)


class FakeExtractor(IListingExtractor):
    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, text: str) -> ExtractedListing:
        self.calls += 1
        if "Ищете жильё" in text:
            return ExtractedListing(is_rental_offer=False)
        rooms = 3 if "Дигомский" in text else 2
        return ExtractedListing(
            is_rental_offer=True,
            city="Tbilisi",
            district="Дигоми" if rooms == 3 else "Ортачала",
            price=850 if rooms == 3 else 750,
            currency="USD",
            rooms=rooms,
            area=100 if rooms == 3 else 68,
            floor=9 if rooms == 3 else None,
            total_floors=18 if rooms == 3 else None,
            title=f"{rooms}-комн. квартира",
        )


def scraper(extractor: FakeExtractor, monkeypatch: pytest.MonkeyPatch) -> TelegramChannelScraper:
    tg = TelegramChannelScraper(
        extractor, channels=("m2tbilis",), delay_seconds=0, max_age_days=100_000
    )

    async def fetch(url: str, expect: str | None = None) -> str:
        return CHANNEL_HTML if url == "https://t.me/s/m2tbilis" else "<html></html>"

    monkeypatch.setattr(tg, "_fetch_page", fetch)
    return tg


async def test_channel_posts_saved_once(
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = FakeExtractor()
    result = await run_scrape(scraper(extractor, monkeypatch), "telegram", 50, session_factory)

    assert (result.scraped, result.valid, result.saved) == (3, 2, 2)
    assert extractor.calls == 3
    repository = ListingsRepository(session)
    flat = await repository.find_by_source("m2tbilis/73972", "telegram")
    assert flat is not None
    assert (flat.rooms, float(flat.area), flat.floor, flat.total_floors) == (3, 100.0, 9, 18)
    assert flat.currency == "GEL", "доллары пересчитаны в лари"
    assert flat.url == "https://t.me/m2tbilis/73972"
    assert flat.description_ru.startswith("Дигомский массив")
    assert flat.title_ru == "3-комн. квартира"
    assert len(flat.images) == 9
    assert flat.details_fetched_at is not None
    skipped = (await session.execute(select(ScrapeSkip.source_id))).scalars().all()
    assert skipped == ["m2tbilis/73971"], "«Ищете жильё?» — не объявление"

    # Второй запуск: всё уже известно — ни одного запроса к AI
    again = FakeExtractor()
    second = await run_scrape(scraper(again, monkeypatch), "telegram", 50, session_factory)
    assert again.calls == 0
    assert second.saved == 0
    count = select(func.count()).select_from(Listing)
    assert (await session.execute(count)).scalar_one() == 2


async def test_old_posts_archived(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    extractor = FakeExtractor()
    factory = async_sessionmaker(session.bind, expire_on_commit=False)
    await run_scrape(scraper(extractor, monkeypatch), "telegram", 50, factory)

    repository = ListingsRepository(session)
    assert (
        await repository.archive_published_before("telegram", datetime(2020, 1, 1, tzinfo=UTC)) == 0
    )
    archived = await repository.archive_published_before(
        "telegram", datetime.now(UTC) + timedelta(days=1)
    )
    await session.commit()
    assert archived == 2
    flat = await repository.find_by_source("m2tbilis/73962", "telegram")
    assert flat is not None and flat.status == ListingStatus.ARCHIVED
