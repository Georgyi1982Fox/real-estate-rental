"""Сравнение квартир (TASK-105) на настоящем PostgreSQL."""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.localization import script_of
from bina.application.ports.scraper import RawListing
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
USERS = {"ru": 784, "en": 785, "ka": 786}


def headers(language: str) -> dict[str, str]:
    return {
        "X-Telegram-Init-Data": sign_init_data(
            BOT_TOKEN, {"id": USERS[language], "first_name": "Anna", "language_code": language}
        )
    }


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def add(session: AsyncSession, source_id: str, **changes: Any) -> Listing:
    values: dict[str, Any] = {
        "source_id": source_id,
        "source_name": "ss",
        "title": "Квартира",
        "description": "",
        "price": 1500,
        "currency": "GEL",
        "rooms": 2,
        "area": 60,
        "district": "Ваке",
        "url": f"https://ss.example/{source_id}",
    }
    values.update(changes)
    listing = await ListingsRepository(session).create_or_update_from_raw(RawListing(**values))
    await session.commit()
    return listing


async def test_compare(client: AsyncClient, session: AsyncSession) -> None:
    vake = await add(session, "vake", features=["furniture", "gas", "air_conditioning"])
    gldani = await add(session, "gldani", price=500, currency="USD", area=90, district="Глдани")
    ids = f"{vake.id},{gldani.id}"

    answer = await client.get("/api/listings/compare", params={"ids": ids}, headers=headers("en"))
    assert answer.status_code == 200
    table = answer.json()
    assert [row["code"] for row in table["rows"]][:3] == ["price", "price_per_m2", "area"]
    assert all(script_of(row["title"]) == "en" for row in table["rows"])
    first, second = table["items"]
    assert first["listing"]["id"] == str(vake.id)
    assert (first["price"], first["district"], first["metro"]) == (1500, "Vake", False)
    assert (second["price"], second["district"], second["metro"]) == (1350, "Gldani", True)
    assert second["price_per_m2"] == 15.0
    assert first["move_in"] > first["price"] * 2
    assert first["price_level"] in ("below", "fair", "above", "unknown")
    assert first["risk_level"] == "none"
    assert table["best"]["price"] == [str(gldani.id)]
    assert table["best"]["area"] == [str(gldani.id)]
    assert table["best"]["minutes_to_center"] == [str(vake.id)]
    assert table["best"]["features"] == [str(vake.id)]
    assert script_of(table["note"]) == "en"

    russian = (
        await client.get(
            "/api/listings/compare",
            params=[("ids", str(vake.id)), ("ids", str(gldani.id))],
            headers=headers("ru"),
        )
    ).json()
    assert russian["items"][1]["district"] == "Глдани"
    assert all(script_of(row["title"]) == "ru" for row in russian["rows"])


async def test_compare_errors(client: AsyncClient, session: AsyncSession) -> None:
    one = await add(session, "one")
    two = await add(session, "two")
    url = "/api/listings/compare"
    for ids in (str(one.id), f"{one.id},{one.id}", f"{one.id},{two.id},{one.id}x,{two.id}y"):
        answer = await client.get(url, params={"ids": ids}, headers=headers("en"))
        assert answer.status_code == 422, ids
    missing = f"{one.id},00000000-0000-0000-0000-000000000000"
    answer = await client.get(url, params={"ids": missing}, headers=headers("en"))
    assert answer.status_code == 404
    # Обычная карточка объявления по-прежнему открывается
    assert (await client.get(f"/api/listings/{one.id}")).status_code == 200
