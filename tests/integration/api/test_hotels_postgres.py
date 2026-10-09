"""Раздел «Гостиницы» (TASK-120): размещение, поиск, номера, жалобы, на PostgreSQL."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User
from tests.integration.api.test_my_listings_postgres import BOT_TOKEN, headers, png

OWNER = 901
GUEST = 902

HOTEL: dict[str, Any] = {
    "kind": "guesthouse",
    "name": "Sea Breeze",
    "city": "batumi",
    "description": "Уютный гостевой дом в пяти минутах от моря, с садом и террасой.",
    "address": "ул. Химшиашвили, 10",
    "latitude": 41.63,
    "longitude": 41.62,
    "stars": 3,
    "amenities": ["wifi", "breakfast", "sea_view", "wifi"],
    "check_in": "14:00",
    "check_out": "12:00",
    "phone": "+995 599 11 22 33",
    "whatsapp": "+995 599 11 22 33",
    "rooms": [
        {"kind": "double", "guests": 2, "price": 120},
        {"kind": "family", "guests": 4, "price": 80, "currency": "USD", "count": 2},
    ],
}


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def create(client: AsyncClient, **changes: Any) -> dict[str, Any]:
    response = await client.post(
        "/api/my/hotels", json={**HOTEL, **changes}, headers=headers(OWNER)
    )
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


async def test_publish_and_find(client: AsyncClient) -> None:
    hotel = await create(client)
    assert hotel["status"] == "active"
    assert hotel["amenities"] == ["wifi", "breakfast", "sea_view"]
    assert hotel["min_price"] == 120.0, "80 $ ≈ 216 ₾ дороже 120 ₾"
    assert hotel["max_guests"] == 4
    assert hotel["description"] == {"ru": HOTEL["description"]}
    assert hotel["phone"] == "+995599112233"

    page = (await client.get("/api/hotels?city=batumi&guests=3")).json()
    assert [item["id"] for item in page["items"]] == [hotel["id"]]
    assert (await client.get("/api/hotels?city=tbilisi")).json()["total"] == 0
    assert (await client.get("/api/hotels?guests=5")).json()["total"] == 0
    assert (await client.get("/api/hotels?price_max=100")).json()["total"] == 0
    assert (await client.get("/api/hotels?amenities=wifi,sea_view")).json()["total"] == 1
    assert (await client.get("/api/hotels?amenities=pool")).json()["total"] == 0
    assert (await client.get("/api/hotels?kind=hotel,hostel")).json()["total"] == 0
    assert (await client.get("/api/hotels?kind=castle")).status_code == 422

    detail = (await client.get(f"/api/hotels/{hotel['id']}")).json()
    assert [room["kind"] for room in detail["rooms"]] == ["double", "family"]
    assert (detail["has_phone"], detail["check_in"]) == (True, "14:00")
    assert "phone" not in detail, "телефон — только после входа"

    assert (await client.get(f"/api/hotels/{hotel['id']}/contact")).status_code == 401
    contact = (
        await client.get(f"/api/hotels/{hotel['id']}/contact", headers=headers(GUEST))
    ).json()
    assert contact["whatsapp_url"] == "https://wa.me/995599112233"
    assert contact["telegram_url"] == "https://t.me/sea_owner"


async def test_rules_reject_spam(client: AsyncClient) -> None:
    rejected = await client.post(
        "/api/my/hotels",
        json={
            **HOTEL,
            "description": "Пишите в WhatsApp +995 599 123 456 или на www.best-hotel.com сразу!",
            "rooms": [{"kind": "double", "guests": 2, "price": 1}],
        },
        headers=headers(OWNER),
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["message"] == "rejected: link_in_text,contact_in_text,bad_price"

    no_contact = await client.post(
        "/api/my/hotels", json={**HOTEL, "phone": None}, headers=headers(OWNER, username=None)
    )
    assert no_contact.status_code == 422


async def test_rooms_photos_and_status(client: AsyncClient) -> None:
    hotel = await create(client, rooms=[])
    me = headers(OWNER)
    # Без номеров объект не в поиске: нет цены
    assert (await client.get("/api/hotels")).json()["total"] == 0

    added = await client.post(
        f"/api/my/hotels/{hotel['id']}/rooms",
        json={"kind": "single", "guests": 1, "price": 60},
        headers=me,
    )
    room_id = added.json()["rooms"][0]["id"]
    assert added.json()["min_price"] == 60.0
    assert (await client.get("/api/hotels")).json()["total"] == 1

    changed = await client.put(
        f"/api/my/hotels/{hotel['id']}/rooms/{room_id}",
        json={"kind": "single", "guests": 1, "price": 75},
        headers=me,
    )
    assert changed.json()["min_price"] == 75.0

    photo = await client.post(
        f"/api/my/hotels/{hotel['id']}/photos",
        content=png(),
        headers={**me, "Content-Type": "image/png"},
    )
    assert photo.status_code == 200, photo.text
    assert len(photo.json()["images"]) == 1
    deleted = await client.delete(f"/api/my/hotels/{hotel['id']}/photos/0", headers=me)
    assert deleted.json()["images"] == []

    off = await client.patch(f"/api/my/hotels/{hotel['id']}", json={"active": False}, headers=me)
    assert off.json()["status"] == "off"
    assert (await client.get(f"/api/hotels/{hotel['id']}")).status_code == 404

    # Чужой объект — как будто его нет
    stranger = headers(GUEST)
    assert (await client.get(f"/api/my/hotels/{hotel['id']}", headers=stranger)).status_code == 404

    removed = await client.delete(f"/api/my/hotels/{hotel['id']}/rooms/{room_id}", headers=me)
    assert removed.json()["rooms"] == []
    assert (await client.delete(f"/api/my/hotels/{hotel['id']}", headers=me)).status_code == 204
    assert (await client.get("/api/my/hotels", headers=me)).json()["items"] == []


async def test_limit_of_active_hotels(client: AsyncClient) -> None:
    for number in range(5):
        await create(client, name=f"Hotel {number}")
    sixth = await client.post("/api/my/hotels", json=HOTEL, headers=headers(OWNER))
    assert sixth.status_code == 409


async def test_complaints_hide_hotel(client: AsyncClient, session: AsyncSession) -> None:
    hotel = await create(client)
    guests = [903, 904, 905]
    for guest in guests:
        await client.get(f"/api/hotels/{hotel['id']}/contact", headers=headers(guest))
    # Жалобы считаются от аккаунтов старше суток
    await session.execute(update(User).values(created_at=datetime.now(UTC) - timedelta(days=2)))
    await session.commit()
    for guest in guests:
        response = await client.post(
            f"/api/hotels/{hotel['id']}/complaints",
            json={"reason": "fraud"},
            headers=headers(guest),
        )
        assert response.status_code == 200, response.text

    assert (await client.get(f"/api/hotels/{hotel['id']}")).status_code == 404
    mine = (await client.get(f"/api/my/hotels/{hotel['id']}", headers=headers(OWNER))).json()
    assert mine["status"] == "hidden"


async def test_options(client: AsyncClient) -> None:
    options = (await client.get("/api/hotels/options")).json()
    assert "guesthouse" in options["kinds"]
    assert "wifi" in options["amenities"]
    assert options["limits"]["active_hotels"] == 5
