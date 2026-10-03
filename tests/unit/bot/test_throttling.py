"""Защита бота от флуда (TASK-019)."""

import pytest
from aiogram.methods import SendMessage

from bina.infrastructure.bot.settings import BotSettings
from tests.support.telegram import TOKEN

from .conftest import BotHarness


@pytest.fixture
def settings() -> BotSettings:
    return BotSettings(token=TOKEN, page_size=3, rate_limit=3)


async def test_flood_is_dropped_with_one_warning(harness: BotHarness) -> None:
    for _ in range(3):
        await harness.send("/help")
    assert len(harness.telegram.of(SendMessage)) == 3
    harness.reset()

    for _ in range(4):
        await harness.send("/help")
    texts = harness.sent_texts()
    assert texts == ["⏳ Слишком много сообщений подряд. Подождите несколько секунд."]
    # Лишние апдейты не открывали сессию БД
    assert len(harness.sessions) == 3


def test_payments_are_never_throttled() -> None:
    """Звёзды уже списаны — успешную оплату и проверку счёта не отбрасываем."""
    from datetime import UTC, datetime

    from aiogram.types import Chat, Message, PreCheckoutQuery, SuccessfulPayment, Update, User

    from bina.infrastructure.bot.middlewares.throttling import _is_payment

    buyer = User(id=1, is_bot=False, first_name="A")
    paid = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=1, type="private"),
        from_user=buyer,
        successful_payment=SuccessfulPayment(
            currency="XTR",
            total_amount=100,
            invoice_payload="plan:month",
            telegram_payment_charge_id="c",
            provider_payment_charge_id="",
        ),
    )
    query = PreCheckoutQuery(
        id="q", from_user=buyer, currency="XTR", total_amount=100, invoice_payload="plan:month"
    )
    assert _is_payment(Update(update_id=1, message=paid))
    assert _is_payment(Update(update_id=2, pre_checkout_query=query))
    text = paid.model_copy(update={"successful_payment": None, "text": "hi"})
    assert not _is_payment(Update(update_id=3, message=text))
