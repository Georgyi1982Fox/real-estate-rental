"""Помесячная и посуточная аренда не смешиваются (TASK-092), на PostgreSQL."""

import dataclasses
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.scrapers.backfill import raw_from_listing


def flat(source_id: str, **fields: Any) -> RawListing:
    base = RawListing(
        source_id=source_id,
        source_name="livo",
        title=f"Квартира {source_id}",
        description="Описание",
        price=1500.0,
        currency="GEL",
        rooms=2,
        area=60.0,
        district="Ваке",
        url=f"https://livo.example/{source_id}",
    )
    return dataclasses.replace(base, **fields)


async def test_search_shows_monthly_by_default(session: AsyncSession) -> None:
    listings = ListingsRepository(session)
    await listings.create_or_update_from_raw(flat("M1"))
    daily = await listings.create_or_update_from_raw(flat("D1", price=80.0, rent_period="daily"))
    await session.commit()

    assert daily.rent_period == "daily"
    assert [item.source_id for item in await listings.search(ListingSearchFilters(), 10)] == ["M1"]
    only_daily = await listings.search(ListingSearchFilters(rent_period="daily"), 10)
    assert [item.source_id for item in only_daily] == ["D1"]
    assert await listings.count(ListingSearchFilters(rent_period=None)) == 2


async def test_update_and_recheck_keep_period(session: AsyncSession) -> None:
    listings = ListingsRepository(session)
    saved = await listings.create_or_update_from_raw(flat("D2", price=90.0, rent_period="daily"))
    await session.commit()
    await session.refresh(saved, attribute_names=["district"])

    # Перепроверка старых объявлений строит RawListing из базы (TASK-018)
    again = await listings.create_or_update_from_raw(raw_from_listing(saved))
    await session.commit()

    assert again.id == saved.id
    assert again.rent_period == "daily"


async def test_price_stats_and_duplicates_by_period(session: AsyncSession) -> None:
    listings = ListingsRepository(session)
    monthly = [
        await listings.create_or_update_from_raw(flat(f"M{i}", price=1500.0 + i)) for i in range(3)
    ]
    daily = await listings.create_or_update_from_raw(flat("D3", price=1500.0, rent_period="daily"))
    await session.commit()
    district = monthly[0].district_id

    count, _ = await listings.rooms_median_price(district, 2, "GEL")
    assert count == 3
    count, median = await listings.rooms_median_price(district, 2, "GEL", "daily")
    assert (count, median) == (1, Decimal(1500))

    # Та же цена и площадь, но посуточно — не дубликат помесячного объявления
    candidates = await listings.duplicate_candidates(monthly[0])
    assert daily.id not in {item.id for item in candidates}
    assert await listings.cheaper_similar(daily, 10) == []
