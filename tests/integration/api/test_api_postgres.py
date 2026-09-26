"""REST API на настоящем PostgreSQL: реальные репозитории и транзакции."""

from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import District, Listing
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
async def listing_ids(session: AsyncSession) -> list[str]:
    district = District(
        name_ru="Ваке", name_ka="ვაკე", name_en="Vake", avg_price_per_m2=Decimal(20),
        safety_score=9,
    )
    session.add(district)
    await session.flush()
    listings = [
        Listing(
            source_id=f"mh-{n}", source_name="myhome", title_ru=f"Квартира {n}",
            title_ka="ბინა", description_ru="", description_ka="",
            price=Decimal(1000 + n * 100), district_id=district.id, rooms=2, area=Decimal(50),
        )
        for n in range(3)
    ]
    session.add_all(listings)
    await session.commit()
    return [str(listing.id) for listing in listings]


async def test_listings(client: AsyncClient, listing_ids: list[str]) -> None:
    body = (await client.get("/api/listings", params={"max_price": "1100"})).json()
    assert body["total"] == 2

    one = await client.get(f"/api/listings/{listing_ids[0]}")
    assert one.status_code == 200
    assert one.json()["title"]["ru"] == "Квартира 0"

    similar = (await client.get(f"/api/listings/{listing_ids[0]}/similar")).json()
    assert {item["id"] for item in similar["items"]} == set(listing_ids[1:])

    districts = (await client.get("/api/districts")).json()
    assert districts["items"][0]["name"]["en"] == "Vake"


async def test_favorites_are_persisted(
    client: AsyncClient,
    session: AsyncSession,
    listing_ids: list[str],
) -> None:
    headers = {
        "X-Telegram-Init-Data": sign_init_data(
            BOT_TOKEN, {"id": 555, "first_name": "Nino", "language_code": "ka"}
        )
    }

    for listing_id in listing_ids[:2]:
        response = await client.post(
            "/api/favorites", json={"listing_id": listing_id}, headers=headers
        )
        assert response.status_code == 201

    count = (await session.execute(text("SELECT count(*) FROM bina_favorites"))).scalar()
    assert count == 2
    language = (await session.execute(text("SELECT language FROM bina_users"))).scalar()
    assert language == "ka"

    response = await client.delete(f"/api/favorites/{listing_ids[0]}", headers=headers)
    assert response.status_code == 204
    body = (await client.get("/api/favorites", headers=headers)).json()
    assert [item["id"] for item in body["items"]] == [listing_ids[1]]
