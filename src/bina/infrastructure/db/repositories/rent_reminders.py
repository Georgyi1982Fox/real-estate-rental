"""Напоминания об оплате аренды (TASK-109)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.use_cases.rent_reminders import DueReminder
from bina.infrastructure.db.models import RentReminder, User


class RentRemindersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: UUID) -> list[RentReminder]:
        query = (
            select(RentReminder)
            .where(RentReminder.user_id == user_id)
            .order_by(RentReminder.day, RentReminder.created_at)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def count_for_user(self, user_id: UUID) -> int:
        query = select(func.count()).where(RentReminder.user_id == user_id)
        return int((await self._session.execute(query)).scalar_one())

    async def add(self, user_id: UUID, day: int, amount: Decimal, currency: str) -> RentReminder:
        reminder = RentReminder(user_id=user_id, day=day, amount=amount, currency=currency)
        self._session.add(reminder)
        await self._session.flush()
        return reminder

    async def delete(self, user_id: UUID, reminder_id: UUID) -> bool:
        result = await self._session.execute(
            delete(RentReminder)
            .where(RentReminder.id == reminder_id, RentReminder.user_id == user_id)
            .returning(RentReminder.id)
        )
        return result.first() is not None

    async def mark_paid(self, user_id: UUID, reminder_id: UUID, due: date) -> bool:
        result = await self._session.execute(
            update(RentReminder)
            .where(RentReminder.id == reminder_id, RentReminder.user_id == user_id)
            .values(paid_for=due)
            .returning(RentReminder.id)
        )
        return result.first() is not None

    # --- IRentRemindersRepository

    async def not_reminded_today(self, today: date) -> list[DueReminder]:
        query = (
            select(RentReminder, User.telegram_id, User.language)
            .join(User, User.id == RentReminder.user_id)
            .where(
                User.is_deleted.is_(False),
                or_(
                    RentReminder.last_reminded_on.is_(None),
                    RentReminder.last_reminded_on < today,
                ),
            )
        )
        rows = (await self._session.execute(query)).all()
        return [
            DueReminder(
                id=reminder.id,
                telegram_id=int(telegram_id),
                language=language,
                day=reminder.day,
                amount=reminder.amount,
                currency=reminder.currency,
                paid_for=reminder.paid_for,
            )
            for reminder, telegram_id, language in rows
        ]

    async def mark_reminded(self, reminder_id: UUID, today: date) -> None:
        await self._session.execute(
            update(RentReminder)
            .where(RentReminder.id == reminder_id)
            .values(last_reminded_on=today)
        )
