"""«Недавно смотрели» и заметки к избранному (TASK-075, TASK-074), на PostgreSQL."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


def headers(user_id: int = 7501) -> dict[str, str]:
    user = {"id": user_id, "first_name": "Nino", "language_code": "ru"}
    return {"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, user)}


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def add(session: AsyncSession, source_id: str) -> Listing:
    listing = await ListingsRepository(session).create_or_update_from_raw(
        RawListing(
            source_id=source_id,
            source_name="ss",
            title="Квартира",
            description="",
            price=1000,
            currency="GEL",
            rooms=2,
            area=50,
            district="Ваке",
            url=f"https://ss.example/{source_id}",
        )
    )
    await session.commit()
    return listing


async def test_recently_viewed(client: AsyncClient, session: AsyncSession) -> None:
    first, second = await add(session, "h1"), await add(session, "h2")
    await client.get(f"/api/listings/{first.id}", headers=headers())
    await client.get(f"/api/listings/{second.id}", headers=headers())
    await client.get(f"/api/listings/{first.id}", headers=headers())  # снова — наверх
    await client.get(f"/api/listings/{second.id}")  # гость — не записывается

    items = (await client.get("/api/history", headers=headers())).json()["items"]
    assert [item["listing"]["id"] for item in items] == [str(first.id), str(second.id)]
    other = (await client.get("/api/history", headers=headers(7502))).json()["items"]
    assert other == [], "у каждого своя история"

    assert (await client.delete("/api/history", headers=headers())).status_code == 204
    assert (await client.get("/api/history", headers=headers())).json()["items"] == []


async def test_notes_on_favorites(client: AsyncClient, session: AsyncSession) -> None:
    listing = await add(session, "n1")
    url = f"/api/favorites/{listing.id}/note"
    missing = await client.put(url, json={"note": "позвонить"}, headers=headers())
    assert missing.status_code == 404, "заметка — только к избранному"

    await client.post("/api/favorites", json={"listing_id": str(listing.id)}, headers=headers())
    saved = await client.put(
        url, json={"note": " Звонил, <b>перезвонить</b> в пятницу "}, headers=headers()
    )
    assert saved.json() == {"listing_id": str(listing.id), "note": "Звонил, перезвонить в пятницу"}
    notes = (await client.get("/api/favorites/notes", headers=headers())).json()["notes"]
    assert notes == {str(listing.id): "Звонил, перезвонить в пятницу"}

    await client.put(url, json={"note": ""}, headers=headers())
    assert (await client.get("/api/favorites/notes", headers=headers())).json()["notes"] == {}
    too_long = await client.put(url, json={"note": "x" * 301}, headers=headers())
    assert too_long.status_code == 422
