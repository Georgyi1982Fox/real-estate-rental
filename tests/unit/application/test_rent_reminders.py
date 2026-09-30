"""Напоминания об оплате аренды (TASK-109): правила и отправка."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from bina.application.rent_reminders import days_left, format_amount, next_due, parse_amount
from bina.application.use_cases.rent_reminders import (
    DueReminder,
    SendRentRemindersUseCase,
    SendResult,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1500", (Decimal(1500), "GEL")),
        ("1 500 лари", (Decimal(1500), "GEL")),
        ("700 $", (Decimal(700), "USD")),
        ("$700", (Decimal(700), "USD")),
        ("650 eur", (Decimal(650), "EUR")),
        ("1,200 USD", (Decimal(1200), "USD")),
        ("1.500", (Decimal(1500), "GEL")),
        ("1500.50", (Decimal("1500.50"), "GEL")),
        ("800 ლარი", (Decimal(800), "GEL")),
    ],
)
def test_parse_amount(text: str, expected: tuple[Decimal, str]) -> None:
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["", "сколько?", "0", "-5", "99999999"])
def test_parse_bad_amount(text: str) -> None:
    assert parse_amount(text) is None


def test_due_dates() -> None:
    assert next_due(date(2026, 10, 3), 5) == date(2026, 10, 5)
    assert next_due(date(2026, 10, 5), 5) == date(2026, 10, 5)
    assert next_due(date(2026, 10, 6), 5) == date(2026, 11, 5)
    assert next_due(date(2026, 12, 30), 2) == date(2027, 1, 2)
    assert days_left(date(2026, 12, 30), 2) == 3
    assert format_amount(Decimal(1500), "GEL") == "1 500 ₾"
    assert format_amount(Decimal("700.50"), "USD") == "700.5 $"


class FakeRepository:
    def __init__(self, reminders: list[DueReminder]) -> None:
        self.reminders = reminders
        self.marked: list[UUID] = []

    async def not_reminded_today(self, today: date) -> list[DueReminder]:
        return self.reminders

    async def mark_reminded(self, reminder_id: UUID, today: date) -> None:
        self.marked.append(reminder_id)


def reminder(day: int, paid_for: date | None = None) -> DueReminder:
    return DueReminder(
        id=uuid4(),
        telegram_id=1,
        language="ru",
        day=day,
        amount=Decimal(1500),
        currency="GEL",
        paid_for=paid_for,
    )


async def test_send_rules() -> None:
    # 12:00 по Тбилиси, 2 октября
    now = datetime(2026, 10, 2, 8, tzinfo=UTC)
    in_3, in_2, in_1, today, paid = (
        reminder(5),
        reminder(4),
        reminder(3),
        reminder(2),
        reminder(3, paid_for=date(2026, 10, 3)),
    )
    blocked, failing = reminder(2), reminder(2)
    results = {blocked.id: SendResult.BLOCKED, failing.id: SendResult.FAILED}
    sent: list[tuple[UUID, int]] = []

    async def sender(reminder: DueReminder, due: date, days: int) -> str:
        sent.append((reminder.id, days))
        return results.get(reminder.id, SendResult.SENT)

    repository = FakeRepository([in_3, in_2, in_1, today, paid, blocked, failing])
    stats = await SendRentRemindersUseCase(repository, sender).execute(now)

    assert sent == [(in_3.id, 3), (in_1.id, 1), (today.id, 0), (blocked.id, 0), (failing.id, 0)]
    assert (stats.sent, stats.failed) == (3, 1)
    # Временная ошибка — не отмечаем, попробуем через час
    assert repository.marked == [in_3.id, in_1.id, today.id, blocked.id]


async def test_not_before_ten_local() -> None:
    early = datetime(2026, 10, 2, 5, tzinfo=UTC)  # 09:00 в Тбилиси

    async def sender(reminder: DueReminder, due: date, days: int) -> str:
        raise AssertionError("не должно отправляться")

    stats = await SendRentRemindersUseCase(FakeRepository([reminder(2)]), sender).execute(early)
    assert (stats.sent, stats.failed) == (0, 0)
