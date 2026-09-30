"""Кому напомнить об окончании Premium (TASK-107)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.use_cases.premium_reminders import Subscriber
from bina.infrastructure.db.models import Notification, NotificationType, User
from bina.infrastructure.db.models.users import SubscriptionTier


class PremiumRemindersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _subscribers(self, *conditions: ColumnElement[bool]) -> list[Subscriber]:
        query = select(User.id, User.subscription_expires_at).where(
            User.is_deleted.is_(False),
            User.subscription_tier != SubscriptionTier.FREE,
            User.subscription_expires_at.is_not(None),
            *conditions,
        )
        rows = (await self._session.execute(query)).all()
        return [
            Subscriber(user_id=user_id, expires_at=expires)
            for user_id, expires in rows
            if expires is not None
        ]

    async def expiring(self, now: datetime, until: datetime) -> list[Subscriber]:
        return await self._subscribers(
            User.subscription_expires_at > now,
            User.subscription_expires_at <= until,
            or_(
                User.premium_reminded_for.is_(None),
                User.premium_reminded_for != User.subscription_expires_at,
            ),
        )

    async def expired(self, since: datetime, now: datetime) -> list[Subscriber]:
        return await self._subscribers(
            User.subscription_expires_at > since,
            User.subscription_expires_at <= now,
            or_(
                User.premium_expired_notified_for.is_(None),
                User.premium_expired_notified_for != User.subscription_expires_at,
            ),
        )

    async def notify(self, user_id: UUID, texts: dict[str, str]) -> None:
        self._session.add(
            Notification(user_id=user_id, type=NotificationType.SYSTEM.value, text=texts)
        )

    async def mark_reminded(self, subscriber: Subscriber) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == subscriber.user_id)
            .values(premium_reminded_for=subscriber.expires_at)
        )

    async def mark_expired_notified(self, subscriber: Subscriber) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == subscriber.user_id)
            .values(premium_expired_notified_for=subscriber.expires_at)
        )
