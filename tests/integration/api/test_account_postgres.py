"""Свои данные: выгрузка и удаление аккаунта (TASK-059, TASK-060), на настоящем PostgreSQL."""

import io
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import Favorite, Listing, Payment, SavedSearch, User
from bina.infrastructure.db.repositories.payments import PaymentsRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
ME = 7301
OTHER = 7302

BODY: dict[str, Any] = {
    "city": "tbilisi",
    "district": "Ваке",
    "rent_period": "monthly",
    "price": 900,
    "rooms": 2,
    "area": 55,
    "description": "Светлая квартира рядом с парком, есть мебель и техника.",
    "phone": "+995555001122",
    "address": "ул. Чавчавадзе, 10",
}


def headers(user_id: int) -> dict[str, str]:
    user = {"id": user_id, "first_name": "Nino", "language_code": "ru", "username": "nino"}
    return {"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, user)}


def png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (40, 30), (10, 90, 160)).save(out, "PNG")
    return out.getvalue()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    app.state.bot_username = "bina_bot"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_export_and_delete_everything(
    client: AsyncClient, session: AsyncSession, tmp_path: Path
) -> None:
    created = await client.post("/api/my/listings", json=BODY, headers=headers(ME))
    assert created.status_code == 201, created.text
    listing_id = created.json()["id"]
    upload = await client.post(
        f"/api/my/listings/{listing_id}/photos",
        content=png(),
        headers={**headers(ME), "Content-Type": "image/png"},
    )
    assert upload.status_code == 200, upload.text
    assert list(tmp_path.rglob("*.jpg")), "фото на диске"
    await client.post("/api/favorites", json={"listing_id": listing_id}, headers=headers(ME))
    await client.post("/api/searches", json={"filters": {"rooms": 2}}, headers=headers(ME))
    me = (await session.execute(select(User).where(User.telegram_id == ME))).scalar_one()
    me_id = me.id
    await PaymentsRepository(session).add_success(me_id, Decimal(100), "XTR", "acc-1", "month")
    await session.commit()
    # Чужие данные не трогаем
    await client.post("/api/favorites", json={"listing_id": listing_id}, headers=headers(OTHER))

    export = await client.get("/api/me/export", headers=headers(ME))
    assert export.status_code == 200
    assert "attachment" in export.headers["content-disposition"]
    data = export.json()
    assert data["profile"]["telegram_id"] == ME
    assert [item["id"] for item in data["listings"]] == [listing_id]
    assert data["listings"][0]["phone"] == "+995555001122"
    assert len(data["favorites"]) == 1 and len(data["saved_searches"]) == 1
    assert Decimal(data["payments"][0]["amount"]) == 100

    assert (await client.delete("/api/me", headers=headers(ME))).status_code == 400, "без confirm"
    deleted = await client.delete("/api/me", params={"confirm": "true"}, headers=headers(ME))
    assert deleted.status_code == 204

    session.expire_all()
    old = await session.get(User, me_id)
    assert old is not None and old.is_deleted and old.telegram_id < 0, "Telegram ID стёрт"
    listing = (await session.execute(select(Listing))).scalar_one()
    assert listing.is_deleted and listing.phone is None and listing.address is None
    assert listing.images == [] and not list(tmp_path.rglob("*.jpg")), "фото стёрты с диска"
    assert listing.owner_user_id is None
    for model in (Favorite, SavedSearch):
        owners = (await session.execute(select(model.user_id))).scalars().all()
        assert me_id not in owners
    other = await UsersRepository(session).get_by_telegram_id(OTHER)
    assert other is not None
    favorites = (await session.execute(select(Favorite.user_id))).scalars().all()
    assert favorites == [other.id]
    payment = (await session.execute(select(Payment))).scalar_one()
    assert payment.user_id == me_id, "платёж остался для бухгалтерии, но без Telegram ID"

    # Снова пришёл — чистый новый аккаунт
    fresh = (await client.get("/api/me", headers=headers(ME))).json()
    assert fresh["favorites_count"] == 0
    assert (await client.get("/api/my/listings", headers=headers(ME))).json()["items"] == []
