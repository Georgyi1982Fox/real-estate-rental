"""Гостиницы в боте (TASK-120, этап 2).

«🏨 Гостиницы» в главном меню и ``/hotels``: несколько объектов кнопками (сначала «🔥 Топ»),
весь раздел и «Разместить» — в приложении. Кнопка объекта или ссылка ``/start h_<id>`` —
карточка: фото, цена «от», вместимость, время заезда, начало описания и кнопки
«✍️ Написать хозяину», «📞 Контакты», «Подробнее в приложении», «Поделиться».

«✍️ Написать хозяину» — диалог через бота с переводом, как у квартир (handlers/chat.py):
сообщение уходит хозяину на его языке, ответ приходит сюда; Telegram друг друга не видно.

«🔥 Топ» гостиницы: счёт ``htop:<id>`` открывает мини-приложение
(``POST /api/my/hotels/{id}/promotion``); проверку перед списанием и запись оплаты
вызывает handlers/payments.py по префиксу счёта.
"""

from datetime import UTC, datetime
from html import escape
from uuid import UUID

import structlog
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.chat import ChatError, ChatErrorCode
from bina.application.cities import city_name
from bina.application.promotion import is_promoted
from bina.application.sharing import hotel_share_link, telegram_share_url
from bina.application.use_cases.chat import ChatUseCase
from bina.application.use_cases.hotel_promotion import HotelPromotionUseCase
from bina.infrastructure.bot.handlers import chat
from bina.infrastructure.bot.keyboards.callbacks import HotelAction, HotelCallback
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import Hotel, User
from bina.infrastructure.db.repositories.chat import ChatRepository
from bina.infrastructure.db.repositories.hotels import HotelFilters, HotelsRepository
from bina.infrastructure.db.repositories.payments import PaymentsRepository

logger = structlog.get_logger(__name__)

DATE_FORMAT = "%d.%m.%Y"
# Столько объектов кнопками в разделе; остальные — в приложении
LIST_SIZE = 8
# Длина названия на кнопке и описания в карточке (подпись к фото — до 1024 знаков)
BUTTON_NAME_MAX = 32
DESCRIPTION_PREVIEW = 300
STAR = "⭐"
TOP = "🔥"


def _app_url(mini_app_url: str | None, path: str) -> str | None:
    return mini_app_url.rstrip("/") + path if mini_app_url else None


def _shorten(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _price(hotel: Hotel) -> str:
    return f"{float(hotel.min_price_gel or 0):.0f}"


def description(hotel: Hotel, language: str) -> str:
    """Описание на языке пользователя; пока не переведено — на языке хозяина."""
    own = getattr(hotel, f"description_{language}", "")
    return own or hotel.description_ru or hotel.description_ka or hotel.description_en or ""


def render_card(hotel: Hotel, language: str, now: datetime) -> str:
    """Текст карточки гостиницы (HTML)."""
    title = f"🏨 <b>{escape(hotel.name)}</b>"
    if hotel.stars:
        title += " " + STAR * hotel.stars
    if is_promoted(hotel.promoted_until, now):
        title = f"{TOP} {title}"
    place = escape(city_name(hotel.city, language))
    if hotel.address:
        place += f", {escape(hotel.address)}"
    lines = [
        title,
        f"{t(language, f'hotel_kind_{hotel.kind}')} · 📍 {place}",
        t(language, "hotel_card_price", price=_price(hotel), guests=hotel.max_guests),
    ]
    if hotel.check_in or hotel.check_out:
        lines.append(
            t(
                language,
                "hotel_card_times",
                check_in=hotel.check_in or "—",
                check_out=hotel.check_out or "—",
            )
        )
    if text := description(hotel, language):
        lines += ["", f"<i>{escape(_shorten(text, DESCRIPTION_PREVIEW))}</i>"]
    return "\n".join(lines)


def card_keyboard(
    hotel: Hotel,
    language: str,
    bot_username: str | None,
    mini_app_url: str | None,
    can_write: bool = True,
) -> InlineKeyboardMarkup:
    """``can_write`` — не своя гостиница: можно написать хозяину."""
    builder = InlineKeyboardBuilder()
    if can_write:
        builder.button(
            text=t(language, "hotel_write_button"),
            callback_data=HotelCallback(action=HotelAction.WRITE, id=hotel.id),
        )
    builder.row(
        InlineKeyboardButton(
            text=t(language, "hotel_contacts_button"),
            callback_data=HotelCallback(action=HotelAction.CONTACTS, id=hotel.id).pack(),
        )
    )
    if url := _app_url(mini_app_url, f"/hotels/{hotel.id}"):
        builder.row(
            InlineKeyboardButton(text=t(language, "card_open_app"), web_app=WebAppInfo(url=url))
        )
    if bot_username:
        link = hotel_share_link(bot_username, hotel.id)
        text = f"{hotel.name} · {t(language, 'hotel_button_price', price=_price(hotel))}"
        builder.row(
            InlineKeyboardButton(
                text=t(language, "share_button"), url=telegram_share_url(link, text)
            )
        )
    return with_home(builder.as_markup(), language)


def photo_url(hotel: Hotel, mini_app_url: str | None) -> str | None:
    """Первое фото по полной ссылке (фото хозяев лежат у нас: /api/media/…)."""
    for image in hotel.images or []:
        if image.startswith(("http://", "https://")):
            return image
        if image.startswith("/") and mini_app_url:
            return mini_app_url.rstrip("/") + image
    return None


async def show_card(
    message: Message,
    user: User,
    session: AsyncSession,
    settings: BotSettings,
    bot: Bot,
    hotel_id: UUID,
) -> None:
    """Карточка гостиницы (кнопка в разделе или ссылка ``/start h_<id>``)."""
    language = user.language
    hotel = await HotelsRepository(session).get_visible(hotel_id)
    if hotel is None:
        await message.answer(
            t(language, "hotel_unavailable"), reply_markup=with_home(None, language)
        )
        return
    text = render_card(hotel, language, datetime.now(UTC))
    username = (await bot.me()).username
    markup = card_keyboard(
        hotel, language, username, settings.mini_app_url, hotel.owner_user_id != user.id
    )
    if photo := photo_url(hotel, settings.mini_app_url):
        try:
            await message.answer_photo(photo, caption=text, reply_markup=markup)
            return
        except TelegramBadRequest as exc:
            logger.info("Hotel photo not sent", error=str(exc))
    await message.answer(text, reply_markup=markup)


# --- Раздел «🏨 Гостиницы»


def section_keyboard(
    hotels: list[Hotel], language: str, mini_app_url: str | None, now: datetime
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for hotel in hotels:
        top = f"{TOP} " if is_promoted(hotel.promoted_until, now) else ""
        text = (
            f"{top}{_shorten(hotel.name, BUTTON_NAME_MAX)} · "
            f"{city_name(hotel.city, language)} · "
            f"{t(language, 'hotel_button_price', price=_price(hotel))}"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=HotelCallback(action=HotelAction.OPEN, id=hotel.id).pack(),
                )
            ]
        )
    if url := _app_url(mini_app_url, "/hotels"):
        rows.append(
            [InlineKeyboardButton(text=t(language, "hotels_all"), web_app=WebAppInfo(url=url))]
        )
    if url := _app_url(mini_app_url, "/my/hotels"):
        rows.append(
            [InlineKeyboardButton(text=t(language, "hotels_mine"), web_app=WebAppInfo(url=url))]
        )
    return with_home(InlineKeyboardMarkup(inline_keyboard=rows), language)


async def cmd_hotels(
    message: Message, user: User, session: AsyncSession, settings: BotSettings
) -> None:
    """/hotels: несколько объектов кнопками, весь раздел — в приложении."""
    language = user.language
    now = datetime.now(UTC)
    hotels, _ = await HotelsRepository(session).search(HotelFilters(), "newest", 1, LIST_SIZE, now)
    key = "hotels_title" if hotels else "hotels_empty"
    await message.answer(
        t(language, key),
        reply_markup=section_keyboard(hotels, language, settings.mini_app_url, now),
    )


async def on_open(
    callback: CallbackQuery,
    callback_data: HotelCallback,
    user: User,
    session: AsyncSession,
    settings: BotSettings,
    bot: Bot,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await show_card(callback.message, user, session, settings, bot, callback_data.id)


def contacts_keyboard(hotel: Hotel, language: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    whatsapp = "".join(char for char in hotel.whatsapp or "" if char.isdigit())
    if whatsapp:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(language, "hotel_whatsapp"), url=f"https://wa.me/{whatsapp}"
                )
            ]
        )
    if hotel.contact_url:
        rows.append(
            [InlineKeyboardButton(text=t(language, "hotel_telegram"), url=hotel.contact_url)]
        )
    return with_home(InlineKeyboardMarkup(inline_keyboard=rows), language)


async def on_contacts(
    callback: CallbackQuery, callback_data: HotelCallback, user: User, session: AsyncSession
) -> None:
    """Телефон и кнопки связи — только по нажатию (не в тексте, который пересылают)."""
    language = user.language
    hotel = await HotelsRepository(session).get_visible(callback_data.id)
    if hotel is None or not isinstance(callback.message, Message):
        await callback.answer(t(language, "hotel_unavailable"), show_alert=True)
        return
    await callback.answer()
    lines = [t(language, "hotel_contacts", name=escape(hotel.name))]
    if hotel.phone:
        lines.append(f"📞 <code>{escape(hotel.phone)}</code>")
    lines += ["", t(language, "hotel_contacts_hint")]
    await callback.message.answer("\n".join(lines), reply_markup=contacts_keyboard(hotel, language))


# --- «✍️ Написать хозяину»


def chat_error(language: str, code: ChatErrorCode) -> str:
    if code == ChatErrorCode.NOT_FOUND:
        return t(language, "hotel_unavailable")
    if code == ChatErrorCode.OWN_LISTING:
        return t(language, "hotel_chat_error_own")
    return chat.error_text(language, code)


async def on_write(
    callback: CallbackQuery,
    callback_data: HotelCallback,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Диалог с хозяином гостиницы; текст сообщения примет chat.on_message."""
    try:
        conversation = await ChatUseCase(ChatRepository(session)).start_hotel(
            callback_data.id, user, datetime.now(UTC)
        )
    except ChatError as exc:
        await callback.answer(chat_error(user.language, exc.code), show_alert=True)
        return
    await chat.ask_message(callback, user, state, conversation.id, "hotel_chat_prompt")


# --- «🔥 Топ» за звёзды (счёт создаёт мини-приложение)


def _promotion(session: AsyncSession) -> HotelPromotionUseCase:
    return HotelPromotionUseCase(HotelsRepository(session), PaymentsRepository(session))


async def check_promotion(query: PreCheckoutQuery, user: User, session: AsyncSession) -> None:
    """Перед списанием звёзд (вызывается из payments.on_pre_checkout)."""
    ok = await _promotion(session).check_payment(
        user.id, query.invoice_payload, query.currency, query.total_amount
    )
    if not ok:
        logger.warning("Hotel promotion pre-checkout rejected", payload=query.invoice_payload)
        await query.answer(ok=False, error_message=t(user.language, "hotel_promo_outdated"))
        return
    await query.answer(ok=True)


async def activate_promotion(
    message: Message, user: User, session: AsyncSession, settings: BotSettings
) -> None:
    """Звёзды списаны: поднять гостиницу в «Топ» (вызывается из payments)."""
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
    language = user.language
    if result is None:
        logger.error(
            "Hotel promotion paid for unknown hotel",
            payload=payment.invoice_payload,
            charge_id=payment.telegram_payment_charge_id,
            telegram_id=user.telegram_id,
        )
        await message.answer(t(language, "hotel_promo_problem"))
        return
    if not result.activated:
        return
    rows: list[list[InlineKeyboardButton]] = []
    if url := _app_url(settings.mini_app_url, "/my/hotels"):
        rows.append(
            [InlineKeyboardButton(text=t(language, "hotels_mine"), web_app=WebAppInfo(url=url))]
        )
    await message.answer(
        t(
            language,
            "hotel_promo_activated",
            name=escape(result.hotel.name),
            date=result.until.strftime(DATE_FORMAT),
        ),
        reply_markup=with_home(InlineKeyboardMarkup(inline_keyboard=rows), language),
    )


def create_router() -> Router:
    router = Router(name="hotels")
    router.message.register(cmd_hotels, Command("hotels"))
    router.callback_query.register(on_open, HotelCallback.filter(F.action == HotelAction.OPEN))
    router.callback_query.register(
        on_contacts, HotelCallback.filter(F.action == HotelAction.CONTACTS)
    )
    router.callback_query.register(on_write, HotelCallback.filter(F.action == HotelAction.WRITE))
    return router
