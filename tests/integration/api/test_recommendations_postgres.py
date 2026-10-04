"""«Вам может понравиться» и «Поделиться» через API (TASK-076, TASK-073), на PostgreSQL."""

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
USER = 7601


def headers(user_id: int = USER, language: str = "ru") -> dict[str, str]:
    user = {"id": user_id, "first_name": "Nino", "language_code": language}
    return {"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, user)}


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    app.state.bot_username = "bina_bot"  # без запроса в Telegram
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def add(
    session: AsyncSession, source_id: str, district: str, rooms: int, price: int
) -> Listing:
    listing = await ListingsRepository(session).create_or_update_from_raw(
        RawListing(
            source_id=source_id,
            source_name="ss",
            title="Квартира",
            description="",
            price=float(price),
            currency="GEL",
            rooms=rooms,
            area=60,
            district=district,
            url=f"https://ss.example/{source_id}",
        )
    )
    await session.commit()
    return listing


async def test_recommendations_follow_favorites(client: AsyncClient, session: AsyncSession) -> None:
    empty = (await client.get("/api/recommendations", headers=headers())).json()
    assert empty == {"items": [], "based_on": 0}, "без избранного подборки нет"

    liked = await add(session, "liked", "Ваке", 2, 1500)
    similar = await add(session, "similar", "Ваке", 2, 1600)
    other = await add(session, "other", "Глдани", 5, 4000)
    await client.post("/api/favorites", json={"listing_id": str(liked.id)}, headers=headers())

    answer = (await client.get("/api/recommendations", headers=headers())).json()
    ids = [item["id"] for item in answer["items"]]
    assert answer["based_on"] == 1
    assert ids[0] == str(similar.id), "та же район, комнаты и цена — первая"
    assert str(liked.id) not in ids, "избранное не предлагаем"
    assert str(other.id) not in ids or ids.index(str(other.id)) > 0
    assert (await client.get("/api/recommendations")).status_code == 401


async def test_share_link(client: AsyncClient, session: AsyncSession) -> None:
    listing = await add(session, "share", "Ваке", 2, 1500)
    answer = await client.get(f"/api/listings/{listing.id}/share", headers=headers(language="en"))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["url"] == f"https://t.me/bina_bot?start=l_{listing.id.hex}"
    assert "1 500 ₾" in body["text"] and "2-room" in body["text"]
    assert body["telegram_url"].startswith("https://t.me/share/url?url=")
    # Гость сайта тоже может поделиться
    guest = await client.get(f"/api/listings/{listing.id}/share", params={"lang": "ka"})
    assert guest.status_code == 200
