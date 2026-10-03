"""«🔥 Топ» за звёзды и «✅ Проверенный собственник» (TASK-097, TASK-098).

Кнопки — в «🏠 Мои объявления» (handlers/owner.py).

Топ: счёт в звёздах ``promo:<id>`` → проверка перед списанием и запись оплаты
(их вызывает handlers/payments.py по префиксу счёта) → объявление 7 дней вверху поиска.

Проверка: хозяин присылает фото или PDF выписки из Публичного реестра → администраторам
(``ADMIN_TELEGRAM_IDS``) приходит документ с кнопками «Подтвердить» / «Отказать» →
решение: значок ✅ у объявления, документ удаляется из чата администратора.
"""

from datetime import UTC, datetime
from html import escape
from uuid import UUID

import structlog
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.owner_listings import MAX_ACTIVE_LISTINGS, OwnerListingError
from bina.application.promotion import (
    PROMOTION_DAYS,
    promotion_payload,
    promotion_price,
)
from bina.application.subscriptions import STARS_CURRENCY
from bina.application.use_cases.promotion import PromotionUseCase, VerificationUseCase
from bina.infrastructure.bot.formatters import format_listing, listing_title
from bina.infrastructure.bot.handlers.admin import is_admin
from bina.infrastructure.bot.handlers.owner import ANSWER
from bina.infrastructure.bot.keyboards.callbacks import (
    AdminAction,
    AdminCallback,
    OwnerAction,
    OwnerCallback,
)
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository
from bina.infrastructure.db.repositories.payments import PaymentsRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from bina.infrastructure.db.repositories.verifications import VerificationsRepository

logger = structlog.get_logger(__name__)

DATE_FORMAT = "%d.%m.%Y"
PHOTO = "photo"
DOCUMENT = "document"
# Сообщение администраторам — по-русски (язык владельца сервиса)
ADMIN_LANGUAGE = "ru"


class VerifyStates(StatesGroup):
    document = State()


def _promotion(session: AsyncSession) -> PromotionUseCase:
    return PromotionUseCase(OwnerListingsRepository(session), PaymentsRepository(session))


def _verification(session: AsyncSession) -> VerificationUseCase:
    return VerificationUseCase(
        OwnerListingsRepository(session),
        VerificationsRepository(session),
        UsersRepository(session),
    )


def _error(language: str, exc: OwnerListingError) -> str:
    return t(language, f"owner_error_{exc.code}", limit=MAX_ACTIVE_LISTINGS)


# --- «🔥 Топ»


async def on_promote(
    callback: CallbackQuery,
    callback_data: OwnerCallback,
    user: User,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Счёт за продвижение своего объявления."""
    if callback_data.listing is None or callback.message is None:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    try:
        listing = await _promotion(session).promotable(user.id, callback_data.listing)
    except OwnerListingError as exc:
        await callback.answer(_error(user.language, exc), show_alert=True)
        return
    title = t(user.language, "promo_invoice_title", days=PROMOTION_DAYS)
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=title,
        description=t(user.language, "promo_invoice_description", days=PROMOTION_DAYS),
        payload=promotion_payload(listing.id),
        currency=STARS_CURRENCY,
        prices=[LabeledPrice(label=title, amount=promotion_price())],
    )
    await callback.answer()


async def check_promotion(query: PreCheckoutQuery, user: User, session: AsyncSession) -> None:
    """Перед списанием звёзд (вызывается из payments.on_pre_checkout)."""
    ok = await _promotion(session).check_payment(
        user.id, query.invoice_payload, query.currency, query.total_amount
    )
    if not ok:
        logger.warning("Promotion pre-checkout rejected", payload=query.invoice_payload)
        await query.answer(ok=False, error_message=t(user.language, "promo_invoice_outdated"))
        return
    await query.answer(ok=True)


async def activate_promotion(message: Message, user: User, session: AsyncSession) -> None:
    """Звёзды списаны: продвинуть объявление (вызывается из payments)."""
    payment = message.successful_payment
    assert payment is not None
    result = await _promotion(session).activate(
        user.id,
        payment.invoice_payload,
        payment.telegram_payment_charge_id,
        payment.total_amount,
        datetime.now(UTC),
    )
    # Звёзды уже списаны: сохраняем сразу, чтобы сбой ответа не откатил оплату
    await session.commit()
    if result is None:
        logger.error(
            "Promotion paid for unknown listing",
            payload=payment.invoice_payload,
            charge_id=payment.telegram_payment_charge_id,
            telegram_id=user.telegram_id,
        )
        await message.answer(t(user.language, "promo_payment_problem"))
        return
    if result.activated:
        await message.answer(
            t(user.language, "promo_activated", date=result.until.strftime(DATE_FORMAT)),
            reply_markup=_my_listings(user.language),
        )


def _my_listings(language: str) -> InlineKeyboardMarkup:
    button = InlineKeyboardButton(
        text=t(language, "owner_my"),
        callback_data=OwnerCallback(action=OwnerAction.LIST).pack(),
    )
    return with_home(InlineKeyboardMarkup(inline_keyboard=[[button]]), language)


# --- «✅ Проверенный собственник»


async def on_verify(
    callback: CallbackQuery,
    callback_data: OwnerCallback,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if callback_data.listing is None or not isinstance(callback.message, Message):
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    try:
        await _verification(session).can_request(user.id, callback_data.listing)
    except OwnerListingError as exc:
        await callback.answer(_error(user.language, exc), show_alert=True)
        return
    await state.set_state(VerifyStates.document)
    await state.update_data(listing=str(callback_data.listing))
    await callback.answer()
    await callback.message.answer(t(user.language, "verify_ask"))


async def on_document(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    settings: BotSettings,
) -> None:
    """Фото или файл документа: заявка и документ администраторам."""
    if message.photo:
        file_id, kind = message.photo[-1].file_id, PHOTO
    else:
        assert message.document is not None
        file_id, kind = message.document.file_id, DOCUMENT
    listing_id = UUID(str((await state.get_data())["listing"]))
    await state.clear()
    try:
        verification, listing = await _verification(session).request(
            user.id, listing_id, file_id, kind, datetime.now(UTC)
        )
    except OwnerListingError as exc:
        await message.answer(_error(user.language, exc))
        return
    # Заявка должна сохраниться до того, как админ нажмёт кнопку
    await session.commit()
    caption = t(ADMIN_LANGUAGE, "verify_admin", listing=format_listing(listing, 1, ADMIN_LANGUAGE))
    markup = decision_keyboard(verification.id)
    for admin_id in settings.admin_ids:
        try:
            if kind == PHOTO:
                await bot.send_photo(admin_id, file_id, caption=caption, reply_markup=markup)
            else:
                await bot.send_document(admin_id, file_id, caption=caption, reply_markup=markup)
        except TelegramAPIError as exc:
            logger.warning("Verification not sent to admin", admin_id=admin_id, error=str(exc))
    await message.answer(
        t(user.language, "verify_sent"), reply_markup=with_home(None, user.language)
    )


async def on_not_document(message: Message, user: User) -> None:
    await message.answer(t(user.language, "verify_send_file"))


def decision_keyboard(verification_id: UUID) -> InlineKeyboardMarkup:
    def button(key: str, action: AdminAction) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=t(ADMIN_LANGUAGE, key),
            callback_data=AdminCallback(action=action, request=verification_id).pack(),
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button("verify_admin_ok_button", AdminAction.VERIFY_OK),
                button("verify_admin_no_button", AdminAction.VERIFY_NO),
            ]
        ]
    )


async def on_decide(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    user: User,
    session: AsyncSession,
    bot: Bot,
    settings: BotSettings,
) -> None:
    """Решение администратора; документ удаляется из его чата."""
    if not is_admin(user, settings) or callback_data.request is None:
        await callback.answer()
        return
    approve = callback_data.action == AdminAction.VERIFY_OK
    try:
        decision = await _verification(session).decide(
            callback_data.request, approve, datetime.now(UTC)
        )
    except OwnerListingError:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    await callback.answer()
    message = callback.message
    if isinstance(message, Message):
        try:
            await message.delete()
        except TelegramAPIError as exc:
            logger.warning("Verification document not deleted", error=str(exc))
        title = escape(listing_title(decision.listing, user.language))
        key = "verify_admin_done_ok" if approve else "verify_admin_done_no"
        await bot.send_message(message.chat.id, t(user.language, key, title=title))
    owner = decision.owner
    owner_title = escape(listing_title(decision.listing, owner.language))
    try:
        await bot.send_message(
            owner.telegram_id,
            t(
                owner.language,
                "verify_approved" if approve else "verify_rejected",
                title=owner_title,
            ),
            reply_markup=_my_listings(owner.language),
        )
    except TelegramAPIError as exc:
        logger.info("Verification answer not delivered", error=str(exc))


def create_router() -> Router:
    router = Router(name="promotion")
    router.message.register(on_document, VerifyStates.document, F.photo | F.document)
    router.message.register(on_not_document, VerifyStates.document, ANSWER)
    router.callback_query.register(
        on_promote, OwnerCallback.filter(F.action == OwnerAction.PROMOTE)
    )
    router.callback_query.register(on_verify, OwnerCallback.filter(F.action == OwnerAction.VERIFY))
    router.callback_query.register(
        on_decide,
        AdminCallback.filter(F.action.in_({AdminAction.VERIFY_OK, AdminAction.VERIFY_NO})),
    )
    return router
