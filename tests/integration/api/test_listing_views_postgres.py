"""Просмотры на карточках и сводка «кто смотрел» без имён (TASK-121), на PostgreSQL."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import Listing, ListingStat
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


def headers(user_id: int) -> dict[str, str]:
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


async def test_views_on_cards_and_summary(client: AsyncClient, session: AsyncSession) -> None:
    seen, unseen = await add(session, "v1"), await add(session, "v2")
    # Две недели назад — 5 просмотров: в «всего», но не в «за неделю»
    old = datetime.now(UTC).date() - timedelta(days=14)
    session.add(ListingStat(listing_id=seen.id, day=old, views=5, contacts=0))
    await session.commit()

    await client.get(f"/api/listings/{seen.id}", headers=headers(8101))
    await client.get(f"/api/listings/{seen.id}", headers=headers(8101))  # тот же человек
    await client.get(f"/api/listings/{seen.id}", headers=headers(8102))
    await client.get(f"/api/listings/{seen.id}")  # гость
    await client.post("/api/favorites", json={"listing_id": str(seen.id)}, headers=headers(8102))

    # В списке поиска у каждой карточки есть число просмотров
    items = (await client.get("/api/listings")).json()["items"]
    views = {item["id"]: item["views"] for item in items}
    assert views == {str(seen.id): 9, str(unseen.id): 0}

    summary = (await client.get(f"/api/listings/{seen.id}/views")).json()
    assert summary == {"total": 9, "today": 4, "week": 4, "people": 2, "in_favorites": 1}
    again = (await client.get(f"/api/listings/{seen.id}/views")).json()
    assert again["total"] == 9, "подсказка сама не считается просмотром"

    # Избранное и «Недавно смотрели» — тоже с числом просмотров
    favorites = (await client.get("/api/favorites", headers=headers(8102))).json()["items"]
    assert [item["views"] for item in favorites] == [9]
    history = (await client.get("/api/history", headers=headers(8101))).json()["items"]
    assert [item["listing"]["views"] for item in history] == [9]

    assert (await client.get(f"/api/listings/{unseen.id}/views")).json()["total"] == 0
    missing = "00000000-0000-0000-0000-000000000000"
    assert (await client.get(f"/api/listings/{missing}/views")).status_code == 404
