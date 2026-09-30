"""Приглашение друзей в боте (TASK-108): /invite, /start ref_<код>, скидка и награда."""

from datetime import UTC, datetime
from decimal import Decimal
from itertools import count

from aiogram.methods import AnswerPreCheckoutQuery, SendInvoice
from aiogram.types import Chat, Message, PreCheckoutQuery, SuccessfulPayment, Update
from aiogram.types import User as TelegramUser

from bina.application.referrals import REWARD_DAYS
from bina.infrastructure.bot.keyboards.callbacks import PremiumBuyCallback
from bina.infrastructure.payments.settings import PREMIUM_MONTH
from tests.support.telegram import BOT_USERNAME, CHAT_ID

from .conftest import BotHarness

_ids = count(50_000)
FRIEND_ID = 888


async def invite_link(harness: BotHarness) -> str:
    await harness.send("/invite")
    text = harness.last_text()
    link = next(word for word in text.split() if word.startswith("https://t.me/"))
    assert link.startswith(f"https://t.me/{BOT_USERNAME}?start=ref_")
    return link


async def friend_starts(harness: BotHarness, link: str) -> None:
    start = link.split("?start=")[1]
    harness.telegram_user = TelegramUser(
        id=FRIEND_ID, is_bot=False, first_name="Giorgi", language_code="en"
    )
    await harness.send(f"/start {start}")


async def friend_pays(harness: BotHarness, amount: int, charge_id: str = "c-1") -> None:
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
                    total_amount=amount,
                    invoice_payload=f"sub:{PREMIUM_MONTH}",
                    telegram_payment_charge_id=charge_id,
                    provider_payment_charge_id="",
                ),
            ),
        ),
    )


async def test_invite_discount_and_reward(harness: BotHarness) -> None:
    await harness.send("/start")
    referrer = harness.user
    link = await invite_link(harness)
    assert "Приглашено: 0" in harness.last_text()

    await friend_starts(harness, link)
    friend = harness.user
    assert friend.referred_by == referrer.id
    assert any("20% off" in text for text in harness.sent_texts())

    # /premium и счёт — со скидкой 20%: 250 → 200 звёзд
    harness.reset()
    await harness.send("/premium")
    assert "200 ⭐" in harness.last_text()
    await harness.press(PremiumBuyCallback(plan=PREMIUM_MONTH).pack())
    [invoice] = harness.telegram.of(SendInvoice)
    assert isinstance(invoice, SendInvoice)
    assert invoice.prices[0].amount == 200

    await harness.dispatcher.feed_update(
        harness.bot,
        Update(
            update_id=next(_ids),
            pre_checkout_query=PreCheckoutQuery(
                id="pcq",
                from_user=harness.telegram_user,
                currency="XTR",
                total_amount=200,
                invoice_payload=f"sub:{PREMIUM_MONTH}",
            ),
        ),
    )
    [answer] = harness.telegram.of(AnswerPreCheckoutQuery)
    assert isinstance(answer, AnswerPreCheckoutQuery)
    assert answer.ok

    await friend_pays(harness, 200)
    assert referrer.subscription_expires_at is not None
    days = (referrer.subscription_expires_at - datetime.now(UTC)).days
    assert REWARD_DAYS - 1 <= days <= REWARD_DAYS
    assert friend.referral_rewarded_at is not None
    [(user_id, texts)] = harness.store.notifications
    assert user_id == referrer.id
    assert f"{REWARD_DAYS} дней Premium" in texts["ru"]

    # Вторая оплата друга — без скидки и без новой награды
    harness.reset()
    await harness.send("/premium")
    assert "250 ⭐" in harness.last_text()
    await friend_pays(harness, 250, charge_id="c-2")
    assert len(harness.store.notifications) == 1
    assert len([p for p in harness.store.payments if p[2] == Decimal(250)]) == 1


async def test_existing_user_and_self_invite_are_ignored(harness: BotHarness) -> None:
    await harness.send("/start")
    me = harness.user
    link = await invite_link(harness)
    # Уже зарегистрированный пользователь (и сам себя) — не становится приглашённым
    await harness.send(f"/start {link.split('?start=')[1]}")
    assert me.referred_by is None
    await harness.send("/start ref_bad")
    assert me.referred_by is None
