"""Подписка Premium за звёзды Telegram (TASK-026/027).

``/premium`` → кнопка «Купить» → счёт (XTR) → ``pre_checkout_query`` (проверка
тарифа и суммы) → ``successful_payment`` (запись платежа и продление подписки).
"""

from datetime import UTC, datetime

import structlog
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.promotion import is_promotion_payload
from bina.application.referrals import FRIEND_DISCOUNT_PERCENT
from bina.application.subscriptions import (
    FREE_LIMITS,
    PREMIUM_LIMITS,
    STARS_CURRENCY,
    Plan,
    is_premium,
    plan_for_payload,
    price_for,
    validate_checkout,
)
from bina.application.use_cases.notifications import FREE_DELIVERY_DELAY
from bina.application.use_cases.referrals import RewardReferrerUseCase
from bina.application.use_cases.subscriptions import ActivateSubscriptionUseCase
from bina.infrastructure.bot.handlers import agency, promotion
from bina.infrastructure.bot.keyboards.callbacks import PremiumBuyCallback
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.payments import PaymentsRepository
from bina.infrastructure.db.repositories.referrals import ReferralsRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from bina.infrastructure.payments import invoice

logger = structlog.get_logger(__name__)

DATE_FORMAT = "%d.%m.%Y"


def render_premium(
    user: User, plans: dict[str, Plan], now: datetime, discounted: bool = False
) -> str:
    """Текущий тариф, что даёт Premium и цена (со скидкой приглашённому другу)."""
    language = user.language
    if is_premium(user, now):
        assert user.subscription_expires_at is not None
        status = t(
            language, "premium_active", date=user.subscription_expires_at.strftime(DATE_FORMAT)
        )
    else:
        status = t(language, "premium_free")
    if discounted:
        status += "\n" + t(language, "premium_discount", percent=FRIEND_DISCOUNT_PERCENT)
    prices = ", ".join(
        t(language, "premium_price", price=price_for(plan, discounted), days=plan.days)
        for plan in sorted(plans.values(), key=lambda plan: plan.days)
    )
    return t(
        language,
        "premium_info",
        status=status,
        free_searches=FREE_LIMITS.searches,
        premium_searches=PREMIUM_LIMITS.searches,
        free_delay=int(FREE_DELIVERY_DELAY.total_seconds() // 3600),
        prices=prices,
    )


def premium_keyboard(
    user: User, plans: dict[str, Plan], now: datetime, discounted: bool = False
) -> InlineKeyboardMarkup:
    """Кнопка покупки (или продления) для каждого тарифа."""
    key = "premium_extend" if is_premium(user, now) else "premium_buy"
    builder = InlineKeyboardBuilder()
    # Короткий срок первым: это самый частый выбор
    for plan in sorted(plans.values(), key=lambda plan: plan.days):
        builder.button(
            text=t(user.language, key, price=price_for(plan, discounted), days=plan.days),
            callback_data=PremiumBuyCallback(plan=plan.id),
        )
    builder.adjust(1)
    return builder.as_markup()


async def cmd_premium(
    message: Message, user: User, plans: dict[str, Plan], session: AsyncSession
) -> None:
    """/premium: тариф и кнопка оплаты."""
    now = datetime.now(UTC)
    discounted = await ReferralsRepository(session).discount_eligible(user)
    await message.answer(
        render_premium(user, plans, now, discounted),
        reply_markup=with_home(premium_keyboard(user, plans, now, discounted), user.language),
    )


async def on_buy(
    callback: CallbackQuery,
    callback_data: PremiumBuyCallback,
    bot: Bot,
    user: User,
    plans: dict[str, Plan],
    session: AsyncSession,
) -> None:
    """Прислать счёт в звёздах (со скидкой, если друг пригласил и это первая покупка)."""
    plan = plans.get(callback_data.plan)
    if plan is None or callback.message is None:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    discounted = await ReferralsRepository(session).discount_eligible(user)
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=invoice.invoice_title(user.language),
        description=invoice.invoice_description(plan, user.language),
        payload=plan.invoice_payload,
        currency=STARS_CURRENCY,
        prices=invoice.invoice_prices(plan, user.language, price_for(plan, discounted)),
    )
    await callback.answer()


async def on_pre_checkout(
    query: PreCheckoutQuery, user: User, plans: dict[str, Plan], session: AsyncSession
) -> None:
    """Последняя проверка перед списанием: тариф существует, сумма и валюта верны.

    Telegram ждёт ответ не дольше 10 секунд.
    """
    if agency.handles_payload(query.invoice_payload):
        # TASK-100: пакет агентства или Premium-объявление
        await agency.check_payment(query, user, session)
        return
    if is_promotion_payload(query.invoice_payload):
        # TASK-097: счёт за «🔥 Топ»
        await promotion.check_promotion(query, user, session)
        return
    discounted = await ReferralsRepository(session).discount_eligible(user)
    plan = validate_checkout(
        plans, query.invoice_payload, query.currency, query.total_amount, discounted
    )
    if plan is None:
        logger.warning(
            "Pre-checkout rejected",
            payload=query.invoice_payload,
            currency=query.currency,
            amount=query.total_amount,
        )
        await query.answer(ok=False, error_message=t(user.language, "premium_invoice_outdated"))
        return
    await query.answer(ok=True)


async def on_successful_payment(
    message: Message, session: AsyncSession, user: User, plans: dict[str, Plan]
) -> None:
    """Деньги списаны: записать платёж и продлить подписку."""
    payment = message.successful_payment
    assert payment is not None
    if agency.handles_payload(payment.invoice_payload):
        await agency.activate_payment(message, user, session)
        return
    if is_promotion_payload(payment.invoice_payload):
        await promotion.activate_promotion(message, user, session)
        return
    plan = plan_for_payload(plans, payment.invoice_payload)
    if plan is None:
        # Тариф убрали между проверкой и оплатой: деньги списаны, разбираемся вручную
        logger.error(
            "Payment for unknown plan",
            payload=payment.invoice_payload,
            charge_id=payment.telegram_payment_charge_id,
            telegram_id=user.telegram_id,
        )
        await message.answer(t(user.language, "premium_payment_problem"))
        return
    result = await ActivateSubscriptionUseCase(
        PaymentsRepository(session), UsersRepository(session)
    ).execute(
        user,
        plan,
        charge_id=payment.telegram_payment_charge_id,
        amount=payment.total_amount,
        now=datetime.now(UTC),
    )
    if result.activated and result.expires_at is not None:
        await message.answer(
            t(user.language, "premium_activated", date=result.expires_at.strftime(DATE_FORMAT))
        )
        # TASK-108: первая оплата приглашённого — награда пригласившему
        await RewardReferrerUseCase(ReferralsRepository(session)).execute(
            user.id, datetime.now(UTC)
        )


async def cmd_paysupport(message: Message, user: User) -> None:
    """/paysupport: обязательна для ботов, принимающих звёзды."""
    await message.answer(
        t(user.language, "paysupport"), reply_markup=with_home(None, user.language)
    )


def create_router() -> Router:
    """Создаёт роутер раздела «payments» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="payments")
    router.message.register(cmd_premium, Command("premium"))
    router.message.register(cmd_paysupport, Command("paysupport"))
    router.message.register(on_successful_payment, F.successful_payment)
    router.callback_query.register(on_buy, PremiumBuyCallback.filter())
    router.pre_checkout_query.register(on_pre_checkout)
    return router
