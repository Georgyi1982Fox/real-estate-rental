"""Анализ цены объявления (TASK-093) на настоящем PostgreSQL."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
HEADERS = {
    "X-Telegram-Init-Data": sign_init_data(
        BOT_TOKEN, {"id": 777, "first_name": "Nino", "language_code": "ru"}
    )
}


def raw(
    source_id: str, price: float, rooms: int = 2, area: float = 60.0, district: str = "Ваке"
) -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="ss",
        title=f"Квартира {source_id}",
        description="",
        price=price,
        currency="GEL",
        rooms=rooms,
        area=area,
        district=district,
        url=f"https://ss.example/{source_id}",
    )


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_price_analysis(client: AsyncClient, session: AsyncSession) -> None:
    repository = ListingsRepository(session)
    # Двушки в Ваке: 1000…1500, медиана 1250
    for n, price in enumerate((1000, 1100, 1200, 1300, 1400, 1500)):
        await repository.create_or_update_from_raw(raw(f"v{n}", price))
    cheap = await repository.create_or_update_from_raw(raw("cheap", 1000))
    # Трёшек в Ваке мало — сравнение по цене за м² (двушки по 60 м²: 16.7…25 ₾/м²)
    big = await repository.create_or_update_from_raw(raw("big", 1500, rooms=3, area=100))
    # В Глдани нет данных
    lonely = await repository.create_or_update_from_raw(raw("lonely", 900, district="Глдани"))
    await session.commit()

    free = (await client.get(f"/api/listings/{cheap.id}/price", headers=HEADERS)).json()
    assert free == {
        "level": "below",
        "diff_percent": None,
        "typical_price": None,
        "currency": "GEL",
        "sample": None,
        "basis": None,
        "premium_required": True,
    }

    await session.execute(
        update(User)
        .where(User.telegram_id == 777)
        .values(
            subscription_tier=SubscriptionTier.NOMAD,
            subscription_expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await session.commit()

    premium = (await client.get(f"/api/listings/{cheap.id}/price", headers=HEADERS)).json()
    # 7 двушек: 1000, 1000, 1100, 1200, 1300, 1400, 1500 — медиана 1200, 1000 на 17% дешевле
    assert premium["level"] == "below"
    assert (premium["diff_percent"], premium["typical_price"], premium["sample"]) == (
        -17,
        1200.0,
        7,
    )
    assert (premium["basis"], premium["premium_required"]) == ("district_rooms", False)

    by_m2 = (await client.get(f"/api/listings/{big.id}/price", headers=HEADERS)).json()
    assert by_m2["basis"] == "district_m2"
    assert by_m2["level"] == "below"  # 15 ₾/м² при медиане 20 ₾/м²

    unknown = (await client.get(f"/api/listings/{lonely.id}/price", headers=HEADERS)).json()
    assert (unknown["level"], unknown["premium_required"]) == ("unknown", False)

    assert (await client.get(f"/api/listings/{cheap.id}/price")).status_code == 401


async def test_risk_report(client: AsyncClient, session: AsyncSession) -> None:
    """TASK-094: причины — всем, объяснения и советы — Premium, на языке пользователя."""
    repository = ListingsRepository(session)
    listing = await repository.create_or_update_from_raw(raw("risky", 400))
    await repository.save_fraud(listing.id, 55, ["prepayment", "price_far_below_market"])
    await session.commit()

    free = (await client.get(f"/api/listings/{listing.id}/risk", headers=HEADERS)).json()
    assert free == {
        "level": "warning",
        "reasons": [
            {"code": "prepayment", "title": None, "explanation": None},
            {"code": "price_far_below_market", "title": None, "explanation": None},
        ],
        "checklist": [],
        "premium_required": True,
    }

    await session.execute(
        update(User)
        .where(User.telegram_id == 777)
        .values(
            subscription_tier=SubscriptionTier.NOMAD,
            subscription_expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await session.commit()
    premium = (await client.get(f"/api/listings/{listing.id}/risk", headers=HEADERS)).json()
    assert premium["premium_required"] is False
    assert premium["reasons"][0]["title"] == "Просят предоплату"  # язык пользователя — ru
    assert premium["checklist"][0] == "Не переводите деньги до просмотра и подписания договора."
    assert len(premium["checklist"]) == 6
