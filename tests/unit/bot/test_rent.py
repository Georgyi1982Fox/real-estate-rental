"""/rent в боте (TASK-109): добавить, «Оплачено», удалить."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from bina.application.rent_reminders import MAX_REMINDERS
from bina.application.use_cases.rent_reminders import DueReminder
from bina.infrastructure.bot.keyboards.callbacks import RentAction, RentCallback
from bina.infrastructure.bot.rent_reminders import render_reminder

from .conftest import BotHarness


async def test_add_pay_and_delete(harness: BotHarness) -> None:
    await harness.send("/rent")
    assert "Напоминаний пока нет" in harness.last_text()

    await harness.press(RentCallback(action=RentAction.ADD).pack())
    assert "Какого числа" in harness.last_text()
    await harness.press(RentCallback(action=RentAction.DAY, day=5).pack())
    assert "Оплата 5-го числа" in harness.last_text()

    await harness.send("сколько?")
    assert "Не понял сумму" in harness.last_text()
    await harness.send("700 $")
    assert "700 $ 5-го числа" in harness.last_text()
    [reminder] = harness.store.rent_reminders
    assert (reminder.day, reminder.amount, reminder.currency) == (5, Decimal(700), "USD")

    # Сообщение напоминания и кнопка «Оплачено»
    await harness.press(
        RentCallback(action=RentAction.PAID, reminder=reminder.id, due="20261105").pack()
    )
    assert reminder.paid_for == date(2026, 11, 5)
    assert "05.11.2026" in harness.last_text()

    await harness.send("/rent")
    assert "оплачено за 05.11.2026" in harness.last_text()

    await harness.press(RentCallback(action=RentAction.DELETE, reminder=reminder.id).pack())
    assert harness.store.rent_reminders == []


async def test_limit_and_foreign_reminder(harness: BotHarness) -> None:
    await harness.send("/rent")
    for day in range(1, MAX_REMINDERS + 1):
        await harness.press(RentCallback(action=RentAction.ADD).pack())
        await harness.press(RentCallback(action=RentAction.DAY, day=day).pack())
        await harness.send("1000")
    assert len(harness.store.rent_reminders) == MAX_REMINDERS
    harness.reset()
    await harness.press(RentCallback(action=RentAction.ADD).pack())
    assert len(harness.store.rent_reminders) == MAX_REMINDERS

    # Чужое напоминание не отмечается
    await harness.press(
        RentCallback(action=RentAction.PAID, reminder=uuid4(), due="20261105").pack()
    )
    assert all(r.paid_for is None for r in harness.store.rent_reminders)


def test_reminder_texts() -> None:
    item = DueReminder(
        id=uuid4(),
        telegram_id=1,
        language="en",
        day=5,
        amount=Decimal(1500),
        currency="GEL",
        paid_for=None,
    )
    assert render_reminder(item, date(2026, 11, 5), 3) == (
        "🗓 Reminder: rent of 1 500 ₾ is due on 05.11.2026 (in 3 days)."
    )
    assert render_reminder(item, date(2026, 11, 5), 0) == "🔔 Rent is due today: 1 500 ₾."
