"""Подписка Premium в боте: /premium, счёт, pre_checkout, successful_payment (TASK-026/027)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count

import pytest
from aiogram.methods import AnswerCallbackQuery, AnswerPreCheckoutQuery, SendInvoice, SendMessage
from aiogram.types import Chat, Message, PreCheckoutQuery, SuccessfulPayment, Update

from bina.infrastructure.bot.keyboards.callbacks import FavoriteToggleCallback, PremiumBuyCallback
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.payments.settings import PREMIUM_MONTH, PREMIUM_WEEK
from tests.support.telegram import CHAT_ID

from .conftest import BotHarness

_ids = count(10_000)
PAYLOAD = f"sub:{PREMIUM_MONTH}"


async def pre_checkout(
    harness: BotHarness, payload: str = PAYLOAD, amount: int = 250, currency: str = "XTR"
) -> AnswerPreCheckoutQuery:
    await harness.dispatcher.feed_update(
        harness.bot,
        Update(
            update_id=next(_ids),
            pre_checkout_query=PreCheckoutQuery(
                id="pcq",
                from_user=harness.telegram_user,
                currency=currency,
                total_amount=amount,
                invoice_payload=payload,
            ),
        ),
    )
    [answer] = harness.telegram.of(AnswerPreCheckoutQuery)
    assert isinstance(answer, AnswerPreCheckoutQuery)
    return answer


async def pay(harness: BotHarness, charge_id: str = "charge-1", payload: str = PAYLOAD) -> None:
    await harness.dispatcher.feed_update(
        harness.bot,
        Update(
            update_id=next(_ids),
            message=Message(
                message_id=next(_ids),
                date=datetime.now(UTC),
                chat=Chat(id=CHAT_ID, type="private"),
                from_user=harness.telegram_user,
                successful_payment=SuccessfulPayment(
                    currency="XTR",
                    total_amount=250,
                    invoice_payload=payload,
                    telegram_payment_charge_id=charge_id,
                    provider_payment_charge_id="",
                ),
            ),
        ),
    )


@pytest.fixture(autouse=True)
def default_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    """Цена по умолчанию, даже если в окружении задана другая."""
    monkeypatch.delenv("PREMIUM_PRICE_STARS", raising=False)
    monkeypatch.delenv("PREMIUM_DAYS", raising=False)
    monkeypatch.delenv("PREMIUM_WEEK_PRICE_STARS", raising=False)
    monkeypatch.delenv("PREMIUM_WEEK_DAYS", raising=False)


async def test_premium_shows_price_and_buy_button(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.reset()

    await harness.send("/premium")

    text = harness.last_text()
    assert "бесплатный тариф" in text
    assert "<b>100 ⭐</b> за 7 дн., <b>250 ⭐</b> за 30 дн." in text
    assert "через 3 ч" in text, "разница тарифов в уведомлениях (TASK-085)"
    [[week], [month]] = harness.last_markup().inline_keyboard
    assert (week.text, month.text) == ("Купить 7 дн. за 100 ⭐", "Купить 30 дн. за 250 ⭐")
    assert week.callback_data == PremiumBuyCallback(plan=PREMIUM_WEEK).pack()
    assert month.callback_data == PremiumBuyCallback(plan=PREMIUM_MONTH).pack()


async def test_buy_sends_stars_invoice(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.reset()

    await harness.press(PremiumBuyCallback(plan=PREMIUM_MONTH).pack())

    [invoice] = harness.telegram.of(SendInvoice)
    assert invoice.chat_id == CHAT_ID
    assert invoice.currency == "XTR"
    assert invoice.payload == PAYLOAD
    assert [price.amount for price in invoice.prices] == [250]
    assert not invoice.provider_token


async def test_buy_week_plan(harness: BotHarness) -> None:
    """TASK-084: недельный пропуск — счёт на 100 ⭐ и продление на 7 дней."""
    await harness.send("/start")
    harness.reset()

    await harness.press(PremiumBuyCallback(plan=PREMIUM_WEEK).pack())

    [invoice] = harness.telegram.of(SendInvoice)
    assert invoice.payload == f"sub:{PREMIUM_WEEK}"
    assert [price.amount for price in invoice.prices] == [100]
    assert "7" in invoice.description


async def test_buy_unknown_plan(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.reset()

    await harness.press(PremiumBuyCallback(plan="old").pack())

    assert harness.telegram.of(SendInvoice) == []
    [answer] = harness.telegram.of(AnswerCallbackQuery)
    assert answer.show_alert


async def test_pre_checkout_accepts_valid_invoice(harness: BotHarness) -> None:
    answer = await pre_checkout(harness)
    assert answer.ok is True


@pytest.mark.parametrize(
    ("payload", "amount", "currency"),
    [
        ("sub:unknown", 250, "XTR"),
        ("other", 250, "XTR"),
        (PAYLOAD, 1, "XTR"),
        (PAYLOAD, 250, "USD"),
    ],
)
async def test_pre_checkout_rejects_wrong_invoice(
    harness: BotHarness, payload: str, amount: int, currency: str
) -> None:
    answer = await pre_checkout(harness, payload, amount, currency)
    assert answer.ok is False
    assert answer.error_message


async def test_successful_payment_activates_premium(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.reset()
    before = datetime.now(UTC)

    await pay(harness)

    user = harness.user
    assert user.subscription_tier == SubscriptionTier.NOMAD
    assert user.subscription_expires_at is not None
    assert user.subscription_expires_at - before >= timedelta(days=30)
    assert harness.store.payments == [(user.id, "charge-1", Decimal(250), PREMIUM_MONTH)]
    assert "Premium действует до" in harness.last_text()


async def test_repeated_payment_update_is_ignored(harness: BotHarness) -> None:
    await harness.send("/start")
    await pay(harness)
    expires = harness.user.subscription_expires_at
    harness.reset()

    await pay(harness)  # Telegram доставил тот же платёж ещё раз

    assert harness.user.subscription_expires_at == expires
    assert len(harness.store.payments) == 1
    assert harness.telegram.of(SendMessage) == []


async def test_second_payment_extends_from_current_expiry(harness: BotHarness) -> None:
    await harness.send("/start")
    await pay(harness, "charge-1")
    first = harness.user.subscription_expires_at
    assert first is not None

    await pay(harness, "charge-2")

    assert harness.user.subscription_expires_at == first + timedelta(days=30)


async def test_payment_for_unknown_plan(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.reset()

    await pay(harness, payload="sub:gone")

    assert harness.user.subscription_tier == SubscriptionTier.FREE
    assert harness.store.payments == []
    assert "/paysupport" in harness.last_text()


async def test_premium_user_sees_expiry_and_extend(harness: BotHarness) -> None:
    await harness.send("/start")
    await pay(harness)
    harness.reset()

    await harness.send("/premium")

    assert "Premium действует до" in harness.last_text()
    [[week], [month]] = harness.last_markup().inline_keyboard
    assert week.text == "Продлить на 7 дн. за 100 ⭐"
    assert month.text == "Продлить на 30 дн. за 250 ⭐"


async def test_paysupport(harness: BotHarness) -> None:
    await harness.send("/paysupport")
    assert "Вопросы по оплате" in harness.last_text()


async def test_favorites_unlimited_on_free_plan(harness: BotHarness) -> None:
    await harness.send("/start")
    district = harness.store.add_district("Ваке")
    listings = [harness.store.add_listing(district) for _ in range(21)]
    for listing in listings[:20]:
        harness.store.favorites.append((harness.user.id, listing.id))
    harness.reset()

    await harness.press(FavoriteToggleCallback(listing_id=listings[20].id).pack())

    assert len(harness.store.favorites) == 21
    [answer] = harness.telegram.of(AnswerCallbackQuery)
    assert not answer.show_alert
