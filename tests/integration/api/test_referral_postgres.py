"""Приглашения (TASK-108) на настоящем PostgreSQL: API, скидка и награда."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.referrals import MONTHLY_REWARDS, REWARD_DAYS
from bina.application.use_cases.referrals import RewardReferrerUseCase
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import Notification, User
from bina.infrastructure.db.repositories.payments import PaymentsRepository
from bina.infrastructure.db.repositories.referrals import ReferralsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


def headers(user_id: int) -> dict[str, str]:
    return {
        "X-Telegram-Init-Data": sign_init_data(
            BOT_TOKEN, {"id": user_id, "first_name": "Anna", "language_code": "en"}
        )
    }


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    app.state.bot_username = "bina_bot"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def user_by_telegram(session: AsyncSession, telegram_id: int) -> User:
    """Свежие данные пользователя (API меняет их в другой сессии)."""
    query = (
        select(User)
        .where(User.telegram_id == telegram_id)
        .execution_options(populate_existing=True)
    )
    return (await session.execute(query)).scalar_one()


async def test_invite_apply_and_discount(client: AsyncClient, session: AsyncSession) -> None:
    mine = (await client.get("/api/referral", headers=headers(1001))).json()
    assert mine["link"] == f"https://t.me/bina_bot?start=ref_{mine['code']}"
    assert (mine["invited"], mine["reward_days"], mine["friend_discount_percent"]) == (0, 7, 20)
    # Код постоянный
    assert (await client.get("/api/referral", headers=headers(1001))).json()["code"] == mine["code"]

    applied = await client.post(
        "/api/referral/apply", json={"code": f"ref_{mine['code']}"}, headers=headers(1002)
    )
    assert applied.json() == {"applied": True, "discount_percent": 20}
    subscription = (await client.get("/api/subscription", headers=headers(1002))).json()
    assert subscription["discount_percent"] == 20
    month = next(plan for plan in subscription["plans"] if plan["id"] == "premium_month")
    assert (month["price_stars"], month["price_stars_for_you"]) == (250, 200)

    # Второй раз и сам себе — не применяется; неверный код — 422
    again = await client.post(
        "/api/referral/apply", json={"code": mine["code"]}, headers=headers(1002)
    )
    assert again.json()["applied"] is False
    own = await client.post(
        "/api/referral/apply", json={"code": mine["code"]}, headers=headers(1001)
    )
    assert own.json() == {"applied": False, "discount_percent": 0}
    for bad in ("zzzzzzzz", "ref_!!"):
        answer = await client.post("/api/referral/apply", json={"code": bad}, headers=headers(1003))
        assert answer.status_code == 422

    # Старый пользователь (больше суток) не может стать приглашённым
    old = await user_by_telegram(session, 1003)
    await session.execute(
        update(User)
        .where(User.id == old.id)
        .values(created_at=datetime.now(UTC) - timedelta(days=2))
    )
    await session.commit()
    late = await client.post(
        "/api/referral/apply", json={"code": mine["code"]}, headers=headers(1003)
    )
    assert late.json()["applied"] is False
    stats = (await client.get("/api/referral", headers=headers(1001))).json()
    assert stats["invited"] == 1


async def test_reward_rules(client: AsyncClient, session: AsyncSession) -> None:
    await client.get("/api/referral", headers=headers(2001))
    referrer_id = (await user_by_telegram(session, 2001)).id
    repository = ReferralsRepository(session)
    now = datetime.now(UTC)

    async def paying_friend(telegram_id: int) -> UUID:
        await client.get("/api/subscription", headers=headers(telegram_id))
        referrer = await user_by_telegram(session, 2001)
        friend = await user_by_telegram(session, telegram_id)
        friend_id = friend.id
        assert await repository.set_referrer(friend, referrer)
        await PaymentsRepository(session).add_success(
            friend_id, Decimal(200), "XTR", f"charge-{telegram_id}", "premium_month"
        )
        await session.commit()
        return friend_id

    first = await paying_friend(2100)
    assert await RewardReferrerUseCase(repository).execute(first, now)
    await session.commit()
    assert not await RewardReferrerUseCase(repository).execute(first, now), "одна награда"
    referrer = await user_by_telegram(session, 2001)
    assert referrer.subscription_expires_at is not None
    assert referrer.subscription_expires_at - now == timedelta(days=REWARD_DAYS)
    notices = select(func.count()).where(Notification.user_id == referrer_id)
    assert (await session.execute(notices)).scalar_one() == 1

    # Лимит наград в месяц
    for index in range(1, MONTHLY_REWARDS + 1):
        friend_id = await paying_friend(2100 + index)
        rewarded = await RewardReferrerUseCase(repository).execute(friend_id, now)
        await session.commit()
        assert rewarded == (index < MONTHLY_REWARDS)
    invited, rewarded_total, this_month = await repository.stats(
        referrer_id, now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    )
    assert (invited, rewarded_total, this_month) == (MONTHLY_REWARDS + 1, 10, 10)
