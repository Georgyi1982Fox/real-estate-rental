"""Отправка напоминаний об оплате аренды (TASK-109). Не коммитит."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from bina.application.rent_reminders import (
    REMIND_DAYS_BEFORE,
    SEND_FROM_HOUR,
    days_left,
    local_now,
    next_due,
)


@dataclass(frozen=True, slots=True)
class DueReminder:
    id: UUID
    telegram_id: int
    language: str
    day: int
    amount: Decimal
    currency: str
    paid_for: date | None


class SendResult:
    SENT = "sent"
    FAILED = "failed"  # временная ошибка — попробуем в следующий час
    BLOCKED = "blocked"  # бот заблокирован — сегодня больше не пытаемся


class IRentRemindersRepository(Protocol):
    async def not_reminded_today(self, today: date) -> list[DueReminder]: ...

    async def mark_reminded(self, reminder_id: UUID, today: date) -> None: ...


class IRentReminderSender(Protocol):
    async def __call__(self, reminder: DueReminder, due: date, days: int) -> str: ...


@dataclass(frozen=True, slots=True)
class RentReminderStats:
    sent: int
    failed: int


class SendRentRemindersUseCase:
    def __init__(self, repository: IRentRemindersRepository, sender: IRentReminderSender) -> None:
        self._repository = repository
        self._sender = sender

    async def execute(self, now: datetime) -> RentReminderStats:
        local = local_now(now)
        if local.hour < SEND_FROM_HOUR:
            return RentReminderStats(sent=0, failed=0)
        today = local.date()
        sent = failed = 0
        for reminder in await self._repository.not_reminded_today(today):
            due = next_due(today, reminder.day)
            left = days_left(today, reminder.day)
            if left not in REMIND_DAYS_BEFORE or reminder.paid_for == due:
                continue
            result = await self._sender(reminder, due, left)
            if result == SendResult.FAILED:
                failed += 1
                continue
            await self._repository.mark_reminded(reminder.id, today)
            sent += result == SendResult.SENT
        return RentReminderStats(sent=sent, failed=failed)
