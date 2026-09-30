"""Объявления собственника через API Mini App (TASK-096), на настоящем PostgreSQL."""

import io
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.owner_listings import MAX_ACTIVE_LISTINGS
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
OWNER = 701
STRANGER = 702

BODY: dict[str, Any] = {
    "city": "batumi",
    "district": "Старый Батуми",
    "rent_period": "daily",
    "price": 120,
    "rooms": 1,
    "area": 40,
    "description": "Уютная студия у моря.\nЕсть кондиционер и Wi-Fi.",
    "features": ["air_conditioning", "internet"],
}


def headers(user_id: int, username: str | None = "sea_owner") -> dict[str, str]:
    user: dict[str, Any] = {"id": user_id, "first_name": "Gio", "language_code": "ru"}
    if username:
        user["username"] = username
    return {"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, user)}


def png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (3000, 2000), (0, 90, 160)).save(out, "PNG")
    return out.getvalue()


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


async def test_post_photos_and_manage(client: AsyncClient) -> None:
    created = await client.post("/api/my/listings", json=BODY, headers=headers(OWNER))
    assert created.status_code == 201, created.text
    listing = created.json()
    assert listing["status"] == "active"
    assert listing["rent_period"] == "daily"
    assert listing["title"]["ru"] == "Посуточно: 1-комн. квартира, Старый Батуми, 40 м²"
    assert listing["title"]["en"] == "Daily: 1-room apartment, Old Batumi, 40 m²"
    assert listing["source_url"] == "https://t.me/sea_owner"
    assert listing["features"] == ["air_conditioning", "internet"]
    assert listing["owner_type"] == "owner"
    listing_id = listing["id"]

    # Сразу в поиске посуточной аренды Батуми
    found = await client.get(
        "/api/listings",
        params={"city": "batumi", "rent_period": "daily", "source": "owner"},
        headers=headers(STRANGER),
    )
    assert [item["id"] for item in found.json()["items"]] == [listing_id]

    upload = await client.post(
        f"/api/my/listings/{listing_id}/photos",
        content=png(),
        headers={**headers(OWNER), "Content-Type": "image/png"},
    )
    assert upload.status_code == 200, upload.text
    [photo] = upload.json()["images"]
    assert photo.startswith("/api/media/listings/")
    served = await client.get(photo)
    assert served.status_code == 200
    with Image.open(io.BytesIO(served.content)) as image:
        assert (image.format, image.size) == ("JPEG", (1600, 1067))

    junk = await client.post(
        f"/api/my/listings/{listing_id}/photos",
        content=b"not an image",
        headers={**headers(OWNER), "Content-Type": "image/jpeg"},
    )
    assert junk.status_code == 422

    stranger = await client.patch(
        f"/api/my/listings/{listing_id}", json={"active": False}, headers=headers(STRANGER)
    )
    assert stranger.status_code == 404

    patched = await client.patch(
        f"/api/my/listings/{listing_id}",
        json={"price": 100, "active": False},
        headers=headers(OWNER),
    )
    assert (patched.json()["price"], patched.json()["status"]) == (100.0, "off")

    deleted = await client.delete(f"/api/my/listings/{listing_id}/photos/0", headers=headers(OWNER))
    assert deleted.json()["images"] == []
    assert (await client.get(photo)).status_code == 404

    mine = (await client.get("/api/my/listings", headers=headers(OWNER))).json()
    assert [item["id"] for item in mine["items"]] == [listing_id]
    assert mine["limit"] == MAX_ACTIVE_LISTINGS
    assert (await client.get("/api/my/listings", headers=headers(STRANGER))).json()["items"] == []


async def test_limits_and_contact(client: AsyncClient) -> None:
    no_contact = await client.post("/api/my/listings", json=BODY, headers=headers(OWNER, None))
    assert no_contact.status_code == 422
    with_phone = await client.post(
        "/api/my/listings",
        json={**BODY, "phone": "+995 555 00 11 22"},
        headers=headers(OWNER, None),
    )
    assert with_phone.status_code == 201
    assert with_phone.json()["has_phone"] is True

    for _ in range(MAX_ACTIVE_LISTINGS - 1):
        assert (
            await client.post("/api/my/listings", json=BODY, headers=headers(OWNER))
        ).status_code == 201
    over = await client.post("/api/my/listings", json=BODY, headers=headers(OWNER))
    assert over.status_code == 409

    bad = await client.post(
        "/api/my/listings", json={**BODY, "description": "<b>коротко</b>"}, headers=headers(OWNER)
    )
    assert bad.status_code == 422
