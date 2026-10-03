"""Переписка с хозяином через бота и запись на просмотр (TASK-111, TASK-112).

Кнопка «💬 N» под результатами поиска (только объявления хозяев, TASK-096) или
ссылка ``t.me/<бот>?start=chat_<id>`` с сайта → карточка квартиры с кнопками
«✍️ Написать хозяину» и «📅 Записаться на просмотр».

Сообщение: бот переводит его на язык получателя (язык бота у хозяина) и пересылает
с кнопкой «↩️ Ответить». Кто есть кто в Telegram, друг другу не показывается.

Просмотр: день → час → хозяин отвечает «✅ Подходит» / «❌ Другое время». О
подтверждённом просмотре бот напоминает обоим за 2 часа (bot/viewing_reminders.py).
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from html import escape
from typing import Any
from uuid import UUID

import structlog
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.chat import (
    MAX_MESSAGE_LENGTH,
    MAX_NEW_CHATS_PER_DAY,
    MAX_PENDING_VIEWINGS,
    ChatError,
    ChatErrorCode,
    local_today,
    viewing_days,
    viewing_hours,
    viewing_start,
)
from bina.application.ports.translator import IMessageTranslator
from bina.application.rent_reminders import TBILISI
from bina.application.use_cases.chat import ChatUseCase, Delivery, ViewingNotice
from bina.infrastructure.bot.formatters import listing_price, listing_title
from bina.infrastructure.bot.handlers.owner import ANSWER
from bina.infrastructure.bot.keyboards.callbacks import ChatAction, ChatCallback
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import Listing, User
from bina.infrastructure.db.repositories.agencies import ListingStatsRepository
from bina.infrastructure.db.repositories.chat import ChatRepository

logger = structlog.get_logger(__name__)

# Лимит Telegram на сообщение 4096; с запасом на разметку
MAX_TELEGRAM_TEXT = 4000
HOURS_PER_ROW = 4
DAYS_PER_ROW = 2
DAY_FORMAT = "%Y%m%d"

# Плейсхолдер {n} в текстах ошибок
_ERROR_LIMITS = {
    ChatErrorCode.LIMIT: MAX_NEW_CHATS_PER_DAY,
    ChatErrorCode.TOO_LONG: MAX_MESSAGE_LENGTH,
    ChatErrorCode.TOO_MANY_VIEWINGS: MAX_PENDING_VIEWINGS,
}
_VIEWING_ERRORS = {
    ChatErrorCode.SLOT_TAKEN,
    ChatErrorCode.SLOT_INVALID,
    ChatErrorCode.TOO_MANY_VIEWINGS,
    ChatErrorCode.ALREADY_ANSWERED,
}


class ChatStates(StatesGroup):
    message = State()


def _use_case(session: AsyncSession, translator: IMessageTranslator | None = None) -> ChatUseCase:
    return ChatUseCase(ChatRepository(session), translator)


def _now() -> datetime:
    return datetime.now(UTC)


def error_text(language: str, code: ChatErrorCode) -> str:
    prefix = "view_error_" if code in _VIEWING_ERRORS else "chat_error_"
    return t(language, prefix + code.value, n=_ERROR_LIMITS.get(code, ""))


def _title(listing: Listing, language: str) -> str:
    return escape(listing_title(listing, language))


def _button(text: str, action: ChatAction, target: UUID, **values: int) -> dict[str, Any]:
    return {"text": text, "callback_data": ChatCallback(action=action, id=target, **values)}


def card_keyboard(language: str, listing_id: UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(**_button(t(language, "chat_write_button"), ChatAction.WRITE, listing_id))
    builder.button(**_button(t(language, "chat_view_button"), ChatAction.VIEW, listing_id))
    builder.adjust(1)
    return with_home(builder.as_markup(), language)


def reply_keyboard(delivery: Delivery) -> InlineKeyboardMarkup:
    language = delivery.recipient.language
    builder = InlineKeyboardBuilder()
    builder.button(
        **_button(t(language, "chat_reply_button"), ChatAction.REPLY, delivery.conversation.id)
    )
    if not delivery.to_owner:
        builder.button(
            **_button(t(language, "chat_view_button"), ChatAction.VIEW, delivery.listing.id)
        )
    builder.adjust(1)
    return builder.as_markup()


def render_delivery(delivery: Delivery) -> str:
    """Сообщение для получателя: перевод (или оригинал) и оригинал мелко."""
    language = delivery.recipient.language
    key = "chat_to_owner" if delivery.to_owner else "chat_to_tenant"
    title = _title(delivery.listing, language)
    body = escape(delivery.translated or delivery.text)
    text = t(language, key, title=title, text=body)
    if delivery.translated:
        original = t(language, "chat_original", text=escape(delivery.text))
        if len(text) + len(original) < MAX_TELEGRAM_TEXT:
            text += f"\n\n<i>{original}</i>"
    return text[:MAX_TELEGRAM_TEXT]


def day_label(language: str, day: date, today: date) -> str:
    if day == today:
        return t(language, "view_today")
    if (day - today).days == 1:
        return t(language, "view_tomorrow")
    weekday = t(language, "weekdays_short").split(",")[day.weekday()]
    return f"{weekday} {day:%d.%m}"


def format_when(language: str, starts_at: datetime) -> str:
    local = starts_at.astimezone(TBILISI)
    weekday = t(language, "weekdays_short").split(",")[local.weekday()]
    return t(language, "view_when", weekday=weekday, date=f"{local:%d.%m}", time=f"{local:%H:%M}")


def _address(language: str, listing: Listing) -> str:
    return t(language, "view_address", address=escape(listing.address)) if listing.address else ""


async def deliver(
    bot: Bot, chat_id: int, text: str, markup: InlineKeyboardMarkup | None = None
) -> bool:
    """Сообщение другому человеку; ``False`` — он остановил бота или чат недоступен."""
    try:
        await bot.send_message(chat_id, text, reply_markup=markup)
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        logger.info("Chat message not delivered", error=str(exc))
        return False
    return True


# --- карточка квартиры


async def show_listing(
    message: Message, user: User, session: AsyncSession, listing_id: UUID
) -> None:
    """Карточка квартиры хозяина с кнопками «Написать» и «Просмотр»."""
    try:
        listing = await _use_case(session).listing_for(listing_id, user)
    except ChatError as exc:
        await message.answer(error_text(user.language, exc.code))
        return
    # TASK-100: открыли карточку — просмотр в статистику хозяина / агентства
    await ListingStatsRepository(session).record(listing, _now().date(), view=True)
    await message.answer(
        t(
            user.language,
            "chat_card",
            title=_title(listing, user.language),
            price=listing_price(listing, user.language),
        ),
        reply_markup=card_keyboard(user.language, listing.id),
    )


async def on_open(
    callback: CallbackQuery, callback_data: ChatCallback, user: User, session: AsyncSession
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_listing(callback.message, user, session, callback_data.id)


# --- сообщения


async def on_write(
    callback: CallbackQuery,
    callback_data: ChatCallback,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    try:
        conversation = await _use_case(session).start(callback_data.id, user, _now())
    except ChatError as exc:
        await callback.answer(error_text(user.language, exc.code), show_alert=True)
        return
    await _ask_message(callback, user, state, conversation.id, "chat_prompt")


async def on_reply(
    callback: CallbackQuery, callback_data: ChatCallback, user: User, state: FSMContext
) -> None:
    await _ask_message(callback, user, state, callback_data.id, "chat_reply_prompt")


async def _ask_message(
    callback: CallbackQuery, user: User, state: FSMContext, conversation_id: UUID, key: str
) -> None:
    await state.set_state(ChatStates.message)
    await state.update_data(conversation=str(conversation_id))
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(t(user.language, key))


async def on_message(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    message_translator: IMessageTranslator | None = None,
) -> None:
    conversation_id = UUID(str((await state.get_data())["conversation"]))
    use_case = _use_case(session, message_translator)
    try:
        delivery = await use_case.send(conversation_id, user, message.text, _now())
    except ChatError as exc:
        if exc.code not in (ChatErrorCode.TOO_LONG, ChatErrorCode.EMPTY):
            await state.clear()
        await message.answer(error_text(user.language, exc.code))
        return
    await state.clear()
    delivered = await deliver(
        bot, delivery.recipient.telegram_id, render_delivery(delivery), reply_keyboard(delivery)
    )
    key = "chat_sent" if delivered else "chat_not_delivered"
    await message.answer(t(user.language, key), reply_markup=with_home(None, user.language))


async def on_not_text(message: Message, user: User) -> None:
    """Фото, стикер и т. п. вместо текста сообщения."""
    await message.answer(t(user.language, "chat_error_empty"))


# --- просмотр


def days_keyboard(language: str, listing_id: UUID, now: datetime) -> InlineKeyboardMarkup:
    today = local_today(now)
    builder = InlineKeyboardBuilder()
    for day in viewing_days(now):
        builder.button(
            **_button(
                day_label(language, day, today),
                ChatAction.DAY,
                listing_id,
                day=int(day.strftime(DAY_FORMAT)),
            )
        )
    builder.adjust(DAYS_PER_ROW)
    return with_home(builder.as_markup(), language)


def hours_keyboard(
    language: str, listing_id: UUID, day: date, hours: list[int]
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    day_value = int(day.strftime(DAY_FORMAT))
    for hour in hours:
        builder.button(
            **_button(f"{hour:02d}:00", ChatAction.TIME, listing_id, day=day_value, hour=hour)
        )
    builder.button(**_button(t(language, "back"), ChatAction.VIEW, listing_id))
    rows = [HOURS_PER_ROW] * ((len(hours) + HOURS_PER_ROW - 1) // HOURS_PER_ROW)
    builder.adjust(*rows, 1)
    return builder.as_markup()


async def _show(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    """Шаг записи на просмотр — тем же сообщением, если можно."""
    message = callback.message
    if not isinstance(message, Message):
        return
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=markup)


async def on_view(
    callback: CallbackQuery, callback_data: ChatCallback, user: User, session: AsyncSession
) -> None:
    try:
        await _use_case(session).listing_for(callback_data.id, user)
    except ChatError as exc:
        await callback.answer(error_text(user.language, exc.code), show_alert=True)
        return
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            t(user.language, "view_choose_day"),
            reply_markup=days_keyboard(user.language, callback_data.id, _now()),
        )


def _day(callback_data: ChatCallback) -> date | None:
    try:
        return datetime.strptime(str(callback_data.day), DAY_FORMAT).date()
    except ValueError:
        return None


async def on_day(
    callback: CallbackQuery, callback_data: ChatCallback, user: User, session: AsyncSession
) -> None:
    day = _day(callback_data)
    if day is None:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    now = _now()
    busy = await _use_case(session).busy_hours(callback_data.id, day)
    hours = [hour for hour in viewing_hours(day, now) if hour not in busy]
    if not hours:
        await callback.answer(t(user.language, "view_no_hours"), show_alert=True)
        return
    await callback.answer()
    await _show(
        callback,
        t(user.language, "view_choose_hour", day=day_label(user.language, day, local_today(now))),
        hours_keyboard(user.language, callback_data.id, day, hours),
    )


async def on_time(
    callback: CallbackQuery,
    callback_data: ChatCallback,
    user: User,
    session: AsyncSession,
    bot: Bot,
) -> None:
    day = _day(callback_data)
    if day is None:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    starts_at = viewing_start(day, callback_data.hour)
    try:
        notice = await _use_case(session).request_viewing(callback_data.id, user, starts_at, _now())
    except ChatError as exc:
        await callback.answer(error_text(user.language, exc.code), show_alert=True)
        return
    await callback.answer()
    owner = notice.owner.language
    await deliver(
        bot,
        notice.owner.telegram_id,
        t(
            owner,
            "view_to_owner",
            title=_title(notice.listing, owner),
            when=format_when(owner, starts_at),
        ),
        answer_keyboard(owner, notice.viewing.id),
    )
    await _show(
        callback,
        t(user.language, "view_requested", when=format_when(user.language, starts_at)),
        with_home(None, user.language),
    )


def answer_keyboard(language: str, viewing_id: UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(**_button(t(language, "view_confirm_button"), ChatAction.CONFIRM, viewing_id))
    builder.button(**_button(t(language, "view_decline_button"), ChatAction.DECLINE, viewing_id))
    builder.adjust(2)
    return builder.as_markup()


async def on_answer(
    callback: CallbackQuery,
    callback_data: ChatCallback,
    user: User,
    session: AsyncSession,
    bot: Bot,
) -> None:
    confirm = callback_data.action == ChatAction.CONFIRM
    try:
        notice = await _use_case(session).answer_viewing(callback_data.id, user, confirm, _now())
    except ChatError as exc:
        await callback.answer(error_text(user.language, exc.code), show_alert=True)
        return
    await callback.answer()
    when = format_when(user.language, notice.viewing.starts_at)
    owner_key = "view_confirmed_owner" if confirm else "view_declined_owner"
    await _show(callback, t(user.language, owner_key, when=when), with_home(None, user.language))
    await deliver(bot, notice.tenant.telegram_id, *tenant_answer(notice, confirm))


def tenant_answer(notice: ViewingNotice, confirm: bool) -> tuple[str, InlineKeyboardMarkup]:
    language = notice.tenant.language
    values = {
        "title": _title(notice.listing, language),
        "when": format_when(language, notice.viewing.starts_at),
    }
    if confirm:
        text = t(
            language,
            "view_confirmed_tenant",
            address=_address(language, notice.listing),
            **values,
        )
        return text, with_home(None, language)
    return t(language, "view_declined_tenant", **values), card_keyboard(language, notice.listing.id)


def render_reminder(notice: ViewingNotice, person: User) -> str:
    language = person.language
    local = notice.viewing.starts_at.astimezone(TBILISI)
    return t(
        language,
        "view_reminder",
        time=f"{local:%H:%M}",
        title=_title(notice.listing, language),
        address=_address(language, notice.listing),
    )


def create_router() -> Router:
    router = Router(name="chat")
    router.message.register(on_message, ChatStates.message, ANSWER)
    router.message.register(on_not_text, ChatStates.message, ~F.text)
    actions: dict[ChatAction, Callable[..., Awaitable[None]]] = {
        ChatAction.OPEN: on_open,
        ChatAction.WRITE: on_write,
        ChatAction.REPLY: on_reply,
        ChatAction.VIEW: on_view,
        ChatAction.DAY: on_day,
        ChatAction.TIME: on_time,
        ChatAction.CONFIRM: on_answer,
        ChatAction.DECLINE: on_answer,
    }
    for action, handler in actions.items():
        router.callback_query.register(handler, ChatCallback.filter(F.action == action))
    return router
