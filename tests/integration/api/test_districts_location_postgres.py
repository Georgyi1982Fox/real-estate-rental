"""Справка по району (TASK-104) и место квартиры на карте (TASK-080) на PostgreSQL."""

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


# Язык запоминается при первом входе: на каждый язык — свой пользователь
USERS = {"ru": 781, "en": 782, "ka": 783}


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
        "price": 1000,
        "currency": "GEL",
        "rooms": 2,
        "area": 50,
        "district": "Ваке",
        "url": f"https://ss.example/{source_id}",
    }
    values.update(changes)
    listing = await ListingsRepository(session).create_or_update_from_raw(RawListing(**values))
    await session.commit()
    return listing


async def test_district_info(client: AsyncClient, session: AsyncSession) -> None:
    listing = None
    for index, price in enumerate((900, 1000, 1100, 1200, 1300)):
        listing = await add(session, f"v{index}", price=price)
    # Двушка в долларах: 400 $ = 1080 ₾ (медиана шести двушек — 1090); трёшек мало — медианы нет
    await add(session, "usd", price=400, currency="USD")
    await add(session, "three", rooms=3, price=2000)
    assert listing is not None
    url = f"/api/districts/{listing.district_id}"

    info = (await client.get(url, headers=headers("ru"))).json()
    assert info["name"] == "Ваке"
    assert info["names"]["en"] == "Vake"
    assert info["listings"] == 7
    assert info["median_rent"] == [{"rooms": 2, "price": 1090}]
    assert info["median_per_m2"] == pytest.approx(22)
    assert info["metro"] is False
    assert 10 <= info["minutes_to_center"] <= 20
    assert script_of(info["about"]) == "ru"
    assert all(script_of(tag["title"]) == "ru" for tag in info["tags"])
    assert script_of(info["note"]) == "ru"

    english = (await client.get(url, headers=headers("en"))).json()
    assert english["name"] == "Vake"
    assert script_of(english["about"]) == "en"
    assert script_of(english["note"]) == "en"

    missing = "/api/districts/00000000-0000-0000-0000-000000000000"
    assert (await client.get(missing, headers=headers("en"))).status_code == 404
    assert (await client.get("/api/districts/abc", headers=headers("en"))).status_code == 404


async def test_location(client: AsyncClient, session: AsyncSession) -> None:
    exact = await add(
        session, "exact", latitude=41.7101, longitude=44.7612, address="Paliashvili 1"
    )
    approximate = await add(session, "approx")
    unknown = await add(session, "unknown", district="Атлантида")

    answer = (await client.get(f"/api/listings/{exact.id}/location", headers=headers("en"))).json()
    assert answer["precision"] == "exact"
    assert (answer["latitude"], answer["longitude"]) == (41.7101, 44.7612)
    assert answer["district"] == "Vake"
    assert "41.710100,44.761200" in answer["links"]["google"]
    assert "pt=44.761200,41.710100" in answer["links"]["yandex"]

    district = (
        await client.get(f"/api/listings/{approximate.id}/location", headers=headers("ka"))
    ).json()
    assert district["precision"] == "district"
    assert district["district"] == "ვაკე"
    assert "pt=" not in district["links"]["yandex"]

    none = (await client.get(f"/api/listings/{unknown.id}/location", headers=headers("en"))).json()
    assert none["precision"] == "none"
    assert none["links"] is None

    # Гость сайта (без входа) тоже видит карту; язык — из ?lang
    guest = await client.get(f"/api/listings/{approximate.id}/location", params={"lang": "ru"})
    assert guest.status_code == 200 and guest.json()["district"] == "Ваке"


async def test_geocode_queue(session: AsyncSession) -> None:
    repository = ListingsRepository(session)
    await add(session, "has_point", latitude=41.71, longitude=44.76, address="A 1")
    no_address = await add(session, "no_address")
    todo = await add(session, "todo", address="Paliashvili 1")
    missing = await add(session, "missing", address="Nowhere 5")

    queue = await repository.to_geocode(10)
    assert {item.id for item in queue} == {todo.id, missing.id}
    assert no_address.id not in {item.id for item in queue}

    await repository.save_location(todo.id, (41.709, 44.758))
    await repository.save_location(missing.id, None)
    await session.commit()
    assert await repository.to_geocode(10) == []
    todo_id = todo.id
    session.expire_all()
    saved = await repository.get_by_id(todo_id)
    assert saved is not None
    assert (saved.latitude, saved.longitude) == (41.709, 44.758)
    assert saved.geocoded_at is not None
