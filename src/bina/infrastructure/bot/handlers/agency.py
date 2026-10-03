"""Кабинет риелтора / агентства в боте (TASK-100).

«🏠 Сдать квартиру» → «💼 Я риелтор / агентство»: название → номер через кнопку
Telegram → кабинет сразу готов (владельцу сервиса — сообщение с кнопкой «Заблокировать»).

Кабинет: пакет, сколько объявлений в поиске из скольких, статистика каждого
объявления за 30 дней, «💳 Пакеты» и «⭐ Premium N». Оплата звёздами — счета
``agency:<пакет>`` и ``bump:<объявление>`` (их проверяет и учитывает handlers/payments.py).
"""

from datetime import UTC, datetime
from html import escape
from typing import Any

import structlog
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.agencies import (
    BUMP_DAYS,
    PLAN_DAYS,
    bump_payload,
    bump_price,
    clean_name,
    free_listings,
    is_agency_payload,
    is_bump_payload,
    load_agency_plans,
    plan_active,
)
from bina.application.owner_listings import OwnerListingError, clean_phone
from bina.application.subscriptions import STARS_CURRENCY, premium_for_all
from bina.application.use_cases.agencies import AgencyUseCase
from bina.infrastructure.bot.formatters import listing_title
from bina.infrastructure.bot.handlers.admin import is_admin
from bina.infrastructure.bot.handlers.owner import ANSWER, owner_limit
from bina.infrastructure.bot.keyboards.callbacks import (
    AdminAction,
    AdminCallback,
    AgencyAction,
    AgencyCallback,
    OwnerAction,
    OwnerCallback,
)
from bina.infrastructure.bot.keyboards.menu import main_menu, with_home
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import Agency, Listing, ListingStatus, User
from bina.infrastructure.db.repositories.agencies import AgenciesRepository
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository
from bina.infrastructure.db.repositories.payments import PaymentsRepository

logger = structlog.get_logger(__name__)

DATE_FORMAT = "%d.%m.%Y"
MAX_TITLE = 50
# Сообщение владельцу сервиса — по-русски
ADMIN_LANGUAGE = "ru"


class AgencyStates(StatesGroup):
    name = State()
    phone = State()


def _use_case(session: AsyncSession) -> AgencyUseCase:
    return AgencyUseCase(
        AgenciesRepository(session),
        load_agency_plans(),
        PaymentsRepository(session),
        OwnerListingsRepository(session),
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _button(text: str, action: AgencyAction, **values: Any) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text, callback_data=AgencyCallback(action=action, **values).pack()
    )


# --- регистрация


async def on_join(
    callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext
) -> None:
    if await AgenciesRepository(session).for_user(user.id) is not None:
        await callback.answer()
        if isinstance(callback.message, Message):
            await show_cabinet(callback.message, user, session)
        return
    await state.set_state(AgencyStates.name)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(user.language, "agency_ask_name", free=free_listings()))


async def on_name(message: Message, user: User, state: FSMContext) -> None:
    name = clean_name(message.text)
    if name is None:
        await message.answer(t(user.language, "agency_bad_name"))
        return
    await state.update_data(name=name)
    await state.set_state(AgencyStates.phone)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(user.language, "agency_phone_button"), request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(t(user.language, "agency_ask_phone"), reply_markup=keyboard)


async def on_phone(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    settings: BotSettings,
) -> None:
    contact = message.contact
    # Только свой номер: кнопка Telegram, а не чужая карточка контакта
    if contact is None or contact.user_id != user.telegram_id:
        await message.answer(t(user.language, "agency_ask_phone"))
        return
    name = str((await state.get_data())["name"])
    try:
        agency = await _use_case(session).register(
            user.id, name, clean_phone(contact.phone_number), "", _now()
        )
    except OwnerListingError as exc:
        await state.clear()
        await message.answer(t(user.language, exc.code), reply_markup=main_menu(user.language))
        return
    await session.commit()
    await state.clear()
    limit, _ = await owner_limit(session, user)
    await message.answer(
        t(user.language, "agency_registered", name=escape(agency.name), limit=limit),
        reply_markup=main_menu(user.language),
    )
    await show_cabinet(message, user, session)
    await _notify_admins(bot, settings, agency)


async def _notify_admins(bot: Bot, settings: BotSettings, agency: Agency) -> None:
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(ADMIN_LANGUAGE, "agency_admin_block"),
                    callback_data=AdminCallback(
                        action=AdminAction.AGENCY_BLOCK, request=agency.id
                    ).pack(),
                )
            ]
        ]
    )
    text = t(
        ADMIN_LANGUAGE,
        "agency_admin_new",
        name=escape(agency.name),
        phone=escape(agency.phone or "—"),
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=markup)
        except TelegramAPIError as exc:
            logger.warning("Agency alert failed", admin_id=admin_id, error=str(exc))


async def on_block(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    user: User,
    session: AsyncSession,
    settings: BotSettings,
) -> None:
    """Владелец сервиса блокирует агентство: его объявления скрыты."""
    if not is_admin(user, settings) or callback_data.request is None:
        await callback.answer()
        return
    agencies = AgenciesRepository(session)
    agency = await agencies.get(callback_data.request)
    if agency is None or agency.blocked_at is not None:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    hidden = await agencies.block(agency, _now())
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            t(user.language, "agency_admin_blocked", name=escape(agency.name), hidden=hidden)
        )


# --- кабинет


async def show_cabinet(message: Message, user: User, session: AsyncSession) -> None:
    language = user.language
    agencies = AgenciesRepository(session)
    agency = await agencies.for_user(user.id)
    if agency is None:
        return
    if agency.blocked_at is not None:
        await message.answer(t(language, "agency_blocked"), reply_markup=with_home(None, language))
        return
    now = _now()
    limit, _ = await owner_limit(session, user)
    stats = await agencies.stats(user.id, now.date())
    active = [item for item in stats if item.listing.status == ListingStatus.ACTIVE]
    lines = []
    for number, item in enumerate(stats, 1):
        until = item.listing.bump_until
        premium = (
            t(language, "agency_premium_mark", date=until.strftime(DATE_FORMAT))
            if until is not None and until > now
            else ""
        )
        lines.append(
            t(
                language,
                "agency_stats_item",
                n=number,
                title=escape(listing_title(item.listing, language)[:MAX_TITLE]),
                premium=premium,
                views=item.views,
                contacts=item.contacts,
                chats=item.chats,
                viewings=item.viewings,
                favorites=item.favorites,
            )
        )
    stats_text = (
        "\n\n".join(lines) + f"\n\n<i>{t(language, 'agency_stats_legend')}</i>"
        if lines
        else t(language, "agency_stats_empty")
    )
    await message.answer(
        t(
            language,
            "agency_card",
            name=escape(agency.name),
            plan=_plan_text(language, agency, now),
            active=len(active),
            limit=limit,
            stats=stats_text,
        ),
        reply_markup=_cabinet_keyboard(language, [item.listing for item in stats]),
    )


def _plan_text(language: str, agency: Agency, now: datetime) -> str:
    if premium_for_all():
        return t(language, "agency_plan_testing")
    plans = load_agency_plans()
    if plan_active(agency.plan, agency.plan_expires_at, now) and agency.plan in plans:
        assert agency.plan_expires_at is not None
        return t(
            language,
            "agency_plan_paid",
            listings=plans[agency.plan].listings,
            date=agency.plan_expires_at.strftime(DATE_FORMAT),
        )
    return t(language, "agency_plan_free")


def _cabinet_keyboard(language: str, listings: list[Listing]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    bump_buttons = 0
    for number, listing in enumerate(listings, 1):
        if listing.status != ListingStatus.ACTIVE or listing.hidden_at is not None:
            continue
        builder.add(
            _button(
                t(language, "agency_bump_button", n=number), AgencyAction.BUMP, listing=listing.id
            )
        )
        bump_buttons += 1
    builder.row(_button(t(language, "agency_plans_button"), AgencyAction.PLANS))
    builder.row(
        InlineKeyboardButton(
            text=t(language, "owner_my"),
            callback_data=OwnerCallback(action=OwnerAction.LIST).pack(),
        )
    )
    rows = [4] * ((bump_buttons + 3) // 4)
    builder.adjust(*rows, 1, 1)
    return with_home(builder.as_markup(), language)


async def on_cabinet(
    callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_cabinet(callback.message, user, session)


# --- пакеты и Premium


async def on_plans(callback: CallbackQuery, user: User) -> None:
    language = user.language
    plans = load_agency_plans()
    builder = InlineKeyboardBuilder()
    for plan in plans.values():
        builder.add(
            _button(
                t(language, "agency_buy_button", listings=plan.listings, price=plan.price_stars),
                AgencyAction.BUY,
                value=plan.id,
            )
        )
    builder.add(_button(t(language, "agency_cabinet"), AgencyAction.CABINET))
    builder.adjust(1)
    lines = "\n".join(
        t(language, "agency_plan_line", listings=plan.listings, price=plan.price_stars)
        for plan in plans.values()
    )
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            t(
                language,
                "agency_plans",
                days=PLAN_DAYS,
                free=free_listings(),
                plans=lines,
                bump=bump_price(),
            ),
            reply_markup=with_home(builder.as_markup(), language),
        )


async def on_buy(
    callback: CallbackQuery,
    callback_data: AgencyCallback,
    user: User,
    session: AsyncSession,
    bot: Bot,
) -> None:
    plan = load_agency_plans().get(callback_data.value or "")
    if plan is None or callback.message is None:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    if await AgenciesRepository(session).for_user(user.id) is None:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    title = t(user.language, "agency_invoice_title", listings=plan.listings)
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=title,
        description=t(
            user.language, "agency_invoice_description", listings=plan.listings, days=plan.days
        ),
        payload=plan.payload,
        currency=STARS_CURRENCY,
        prices=[LabeledPrice(label=title, amount=plan.price_stars)],
    )
    await callback.answer()


async def on_bump(
    callback: CallbackQuery,
    callback_data: AgencyCallback,
    user: User,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if callback_data.listing is None or not isinstance(callback.message, Message):
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    use_case = _use_case(session)
    try:
        if premium_for_all():
            # Тестовый режим: Premium-объявление без оплаты
            paid = await use_case.bump_for_free(user.id, callback_data.listing, _now())
            await session.commit()
            await callback.answer()
            await _bump_done(callback.message, user, paid.listing, paid.until)
            return
        listing = await use_case.bumpable(user.id, callback_data.listing)
    except OwnerListingError as exc:
        await callback.answer(t(user.language, f"owner_error_{exc.code}", limit=0), show_alert=True)
        return
    title = t(user.language, "agency_bump_title")
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=title,
        description=t(user.language, "agency_bump_description", days=BUMP_DAYS),
        payload=bump_payload(listing.id),
        currency=STARS_CURRENCY,
        prices=[LabeledPrice(label=title, amount=bump_price())],
    )
    await callback.answer()


async def _bump_done(
    message: Message, user: User, listing: Listing | None, until: datetime
) -> None:
    assert listing is not None
    title = escape(listing_title(listing, user.language))
    await message.answer(
        t(user.language, "agency_bump_activated", title=title, date=until.strftime(DATE_FORMAT)),
        reply_markup=_back_to_cabinet(user.language),
    )


def _back_to_cabinet(language: str) -> InlineKeyboardMarkup:
    return with_home(
        InlineKeyboardMarkup(
            inline_keyboard=[[_button(t(language, "agency_cabinet"), AgencyAction.CABINET)]]
        ),
        language,
    )


# --- оплата (вызывается из handlers/payments.py по префиксу счёта)


def handles_payload(payload: str) -> bool:
    return is_agency_payload(payload) or is_bump_payload(payload)


async def check_payment(query: PreCheckoutQuery, user: User, session: AsyncSession) -> None:
    use_case = _use_case(session)
    payload = query.invoice_payload
    if is_agency_payload(payload):
        ok = (
            use_case.check_plan_payment(payload, query.currency, query.total_amount) is not None
            and await AgenciesRepository(session).for_user(user.id) is not None
        )
    else:
        ok = await use_case.check_bump_payment(user.id, payload, query.currency, query.total_amount)
    if not ok:
        logger.warning("Agency pre-checkout rejected", payload=payload)
        await query.answer(ok=False, error_message=t(user.language, "agency_invoice_outdated"))
        return
    await query.answer(ok=True)


async def activate_payment(message: Message, user: User, session: AsyncSession) -> None:
    payment = message.successful_payment
    assert payment is not None
    use_case = _use_case(session)
    args = (
        user.id,
        payment.invoice_payload,
        payment.telegram_payment_charge_id,
        payment.total_amount,
        _now(),
    )
    if is_agency_payload(payment.invoice_payload):
        paid = await use_case.activate_plan(*args)
    else:
        paid = await use_case.activate_bump(*args)
    # Звёзды уже списаны: сохраняем сразу, чтобы сбой ответа не откатил оплату
    await session.commit()
    if paid is None:
        logger.error(
            "Agency payment for unknown plan or listing",
            payload=payment.invoice_payload,
            charge_id=payment.telegram_payment_charge_id,
            telegram_id=user.telegram_id,
        )
        await message.answer(t(user.language, "agency_payment_problem"))
        return
    if not paid.activated:
        return
    if paid.plan is not None:
        await message.answer(
            t(
                user.language,
                "agency_plan_activated",
                listings=paid.plan.listings,
                date=paid.until.strftime(DATE_FORMAT),
            ),
            reply_markup=_back_to_cabinet(user.language),
        )
    elif paid.listing is not None:
        await _bump_done(message, user, paid.listing, paid.until)


def create_router() -> Router:
    router = Router(name="agency")
    router.message.register(on_name, AgencyStates.name, ANSWER)
    router.message.register(on_phone, AgencyStates.phone, F.contact)
    router.message.register(on_phone, AgencyStates.phone, ANSWER)

    def action(value: AgencyAction) -> Any:
        return AgencyCallback.filter(F.action == value)

    router.callback_query.register(on_join, action(AgencyAction.JOIN))
    router.callback_query.register(on_cabinet, action(AgencyAction.CABINET))
    router.callback_query.register(on_plans, action(AgencyAction.PLANS))
    router.callback_query.register(on_buy, action(AgencyAction.BUY))
    router.callback_query.register(on_bump, action(AgencyAction.BUMP))
    router.callback_query.register(
        on_block, AdminCallback.filter(F.action == AdminAction.AGENCY_BLOCK)
    )
    return router
