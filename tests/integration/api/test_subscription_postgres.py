"""Подписка Premium на настоящем PostgreSQL (TASK-026/027).

Бесплатный тариф: 1 сохранённый поиск (второй — 402). Оплата: платёж записывается
(enum-ы хранятся значениями), подписка продлевается, повтор того же платежа
ничего не меняет. После оплаты лимиты сняты.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.use_cases.subscriptions import ActivateSubscriptionUseCase
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.db.repositories.payments import PaymentsRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from bina.infrastructure.payments.settings import PREMIUM_MONTH, PREMIUM_WEEK, load_plans
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
USER = {"id": 777, "first_name": "Nino", "language_code": "ru"}
HEADERS = {"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, USER)}


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def activate(
    session_factory: async_sessionmaker[AsyncSession], charge_id: str
) -> datetime | None:
    plan = load_plans({})[PREMIUM_MONTH]
    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.telegram_id == 777))).scalar_one()
        use_case = ActivateSubscriptionUseCase(
            PaymentsRepository(session), UsersRepository(session)
        )
        result = await use_case.execute(
            user, plan, charge_id=charge_id, amount=250, now=datetime.now(UTC)
        )
        await session.commit()
        return result.expires_at


async def test_free_limits_and_premium(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    body = (await client.get("/api/subscription", headers=HEADERS)).json()
    assert (body["tier"], body["is_premium"], body["expires_at"]) == ("free", False, None)
    assert body["limits"] == {"favorites": None, "searches": 1}
    assert body["usage"] == {"favorites": 0, "searches": 0}
    assert body["plans"] == [
        {
            "id": PREMIUM_MONTH,
            "tier": "nomad",
            "days": 30,
            "price_stars": 250,
            "price_stars_for_you": 250,
        },
        {
            "id": PREMIUM_WEEK,
            "tier": "nomad",
            "days": 7,
            "price_stars": 100,
            "price_stars_for_you": 100,
        },
    ]

    first = await client.post("/api/searches", json={"filters": {"rooms": 2}}, headers=HEADERS)
    assert first.status_code == 201
    second = await client.post("/api/searches", json={"filters": {"rooms": 3}}, headers=HEADERS)
    assert second.status_code == 402
    assert second.json()["error"]["code"] == "payment_required"

    expires = await activate(session_factory, "charge-1")
    assert expires is not None
    assert expires - datetime.now(UTC) > timedelta(days=29)
    # Повторная доставка того же платежа
    assert await activate(session_factory, "charge-1") == expires

    async with session_factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT provider::text, status::text, amount, currency, plan FROM bina_payments"
                )
            )
        ).all()
    assert [tuple(row) for row in rows] == [
        ("telegram_stars", "success", 250, "XTR", PREMIUM_MONTH)
    ]

    me = (await client.get("/api/me", headers=HEADERS)).json()
    assert (me["subscription_tier"], me["is_premium"]) == (SubscriptionTier.NOMAD.value, True)
    body = (await client.get("/api/subscription", headers=HEADERS)).json()
    assert body["limits"] == {"favorites": None, "searches": 20}
    assert body["usage"]["searches"] == 1
    again = await client.post("/api/searches", json={"filters": {"rooms": 3}}, headers=HEADERS)
    assert again.status_code == 201

    # Второй платёж продлевает от текущей даты окончания
    assert await activate(session_factory, "charge-2") == expires + timedelta(days=30)
