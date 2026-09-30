"""Напоминания об окончании Premium (TASK-107) на настоящем PostgreSQL."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.localization import script_of
from bina.application.use_cases.premium_reminders import (
    EXPIRED,
    REMINDER,
    PremiumRemindersUseCase,
)
from bina.infrastructure.db.models import Notification, User
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.db.repositories.notifications import NotificationsRepository
from bina.infrastructure.db.repositories.premium_reminders import PremiumRemindersRepository
from bina.infrastructure.db.repositories.users import UsersRepository

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)


async def premium_user(session: AsyncSession, telegram_id: int, expires: datetime | None) -> User:
    user = await UsersRepository(session).create(telegram_id, "ru")
    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            subscription_tier=SubscriptionTier.NOMAD if expires else SubscriptionTier.FREE,
            subscription_expires_at=expires,
        )
    )
    await session.commit()
    return user


async def texts_for(session: AsyncSession, user: User) -> list[str]:
    query = (
        select(Notification.text)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at)
    )
    rows: Sequence[dict[str, Any] | None] = (await session.execute(query)).scalars().all()
    return [str(text["ru"]) for text in rows if text]


async def run(session: AsyncSession, now: datetime = NOW) -> tuple[int, int]:
    stats = await PremiumRemindersUseCase(PremiumRemindersRepository(session)).execute(now)
    await session.commit()
    return stats.reminded, stats.expired


async def test_reminders(session: AsyncSession) -> None:
    soon = await premium_user(session, 1, NOW + timedelta(days=2))
    later = await premium_user(session, 2, NOW + timedelta(days=10))
    ended = await premium_user(session, 3, NOW - timedelta(hours=5))
    long_ago = await premium_user(session, 4, NOW - timedelta(days=30))
    free = await premium_user(session, 5, None)

    assert await run(session) == (1, 1)
    assert await texts_for(session, soon) == [REMINDER["ru"].format(date="12.10.2026")]
    assert await texts_for(session, ended) == [EXPIRED["ru"]]
    for user in (later, long_ago, free):
        assert await texts_for(session, user) == []

    # Повторный запуск — ничего нового
    assert await run(session) == (0, 0)

    # Продлил — напомним снова, когда подойдёт новый срок
    await session.execute(
        update(User)
        .where(User.id == soon.id)
        .values(subscription_expires_at=NOW + timedelta(days=32))
    )
    await session.commit()
    assert await run(session) == (0, 0)
    assert await run(session, NOW + timedelta(days=30)) == (1, 0)
    assert len(await texts_for(session, soon)) == 2


async def test_system_messages_skip_free_delay(session: AsyncSession) -> None:
    ended = await premium_user(session, 6, NOW - timedelta(hours=1))
    await run(session)
    # Пользователь уже без Premium, но служебное сообщение уходит сразу
    pending = await NotificationsRepository(session).list_unsent(
        10, free_created_before=datetime.now(UTC) - timedelta(hours=3)
    )
    assert [item.notification.user_id for item in pending] == [ended.id]


def test_texts_in_every_language() -> None:
    for texts in (REMINDER, EXPIRED):
        for language in ("ka", "ru", "en"):
            assert script_of(texts[language]) == language
            assert "/premium" in texts[language]
