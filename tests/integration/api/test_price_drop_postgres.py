"""«📉 Цена снижена» (FRONTEND-055): ``old_price`` в ответе и фильтр ``price_dropped``."""

import dataclasses
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository


def raw(source_id: str, **fields: Any) -> RawListing:
    base = RawListing(
        source_id=source_id,
        source_name="ss",
        title=f"Квартира {source_id}",
        description="Описание",
        price=1500.0,
        currency="USD",
        rooms=2,
        area=60.0,
        district="Ваке",
        url=f"https://home.ss.ge/ru/{source_id}",
    )
    return dataclasses.replace(base, **fields)


async def by_url(client: AsyncClient, query: str = "") -> dict[str, dict[str, Any]]:
    body = (await client.get(f"/api/listings?per_page=50&{query}")).json()
    assert "items" in body, body
    return {item["source_url"].rsplit("/", 1)[-1]: item for item in body["items"]}


async def test_price_drop_shown_and_filtered(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    repository = ListingsRepository(session)
    for source_id in ("cheaper", "pricier", "old_drop", "same"):
        await repository.create_or_update_from_raw(raw(source_id))
    await session.commit()
    # Сайт поменял цены: подешевели две, одна подорожала
    await repository.create_or_update_from_raw(raw("cheaper", price=1300.0))
    await repository.create_or_update_from_raw(raw("pricier", price=1700.0))
    await repository.create_or_update_from_raw(raw("old_drop", price=1200.0))
    await session.commit()
    # Снижение 40 дней назад — уже не новость
    await session.execute(
        update(Listing)
        .where(Listing.source_id == "old_drop")
        .values(price_changed_at=datetime.now(UTC) - timedelta(days=40))
    )
    await session.commit()

    app = create_app(ApiSettings(), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        items = await by_url(client)
        assert items["cheaper"]["old_price"] == 1500.0
        assert items["cheaper"]["price"] == 1300.0
        assert items["cheaper"]["price_dropped_at"] is not None
        for other in ("pricier", "old_drop", "same"):
            assert items[other]["old_price"] is None
            assert items[other]["price_dropped_at"] is None

        assert list(await by_url(client, "price_dropped=true")) == ["cheaper"]
        assert len(await by_url(client, "price_dropped=false")) == 4

        listing_id = items["cheaper"]["id"]
        page = (await client.get(f"/api/listings/{listing_id}")).json()
        assert page["old_price"] == 1500.0


async def test_other_currency_is_not_a_drop(session: AsyncSession) -> None:
    """2000 ₾ → 750 $ — не «подешевело»: цены в разных валютах не сравниваются."""
    repository = ListingsRepository(session)
    await repository.create_or_update_from_raw(raw("fx", price=2000.0, currency="GEL"))
    await session.commit()
    await repository.create_or_update_from_raw(raw("fx", price=750.0, currency="USD"))
    await session.commit()

    listing = (await session.execute(select(Listing).where(Listing.source_id == "fx"))).scalar_one()
    assert listing.previous_price is None
    assert listing.price_changed_at is not None
