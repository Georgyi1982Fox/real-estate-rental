"""Сообщение владельцу сервиса о новой гостинице (TASK-120).

Объект сразу в поиске; владелец видит его в Telegram и может скрыть одной кнопкой.
"""

from collections.abc import Iterable
from html import escape

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bina.application.cities import city_name
from bina.infrastructure.bot.keyboards.callbacks import AdminAction, AdminCallback
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import Hotel, User

logger = structlog.get_logger(__name__)

# Столько знаков описания в сообщении владельцу
DESCRIPTION_PREVIEW = 300


async def notify_admins_hotel(
    bot: Bot, admin_ids: Iterable[int], hotel: Hotel, author: User
) -> None:
    """Каждому админу — карточка объекта, начало описания и кнопка «Скрыть»."""
    description = hotel.description_ru or hotel.description_ka or hotel.description_en
    for admin_id in admin_ids:
        language = author.language if author.telegram_id == admin_id else "ru"
        text = t(
            language,
            "hotel_admin_new",
            name=escape(hotel.name),
            kind=hotel.kind,
            city=escape(city_name(hotel.city, language)),
            rooms=len(hotel.rooms),
            price=f"{float(hotel.min_price_gel):.0f}" if hotel.min_price_gel else "—",
            photos=len(hotel.images or []),
            author=escape(str(author.telegram_id)),
            description=escape(description[:DESCRIPTION_PREVIEW]),
        )
        button = InlineKeyboardButton(
            text=t(language, "owner_admin_hide"),
            callback_data=AdminCallback(action=AdminAction.HOTEL_HIDE, listing=hotel.id).pack(),
        )
        try:
            await bot.send_message(
                admin_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[button]])
            )
        except TelegramAPIError as exc:
            # Сообщение владельцу не должно ломать размещение
            logger.warning("Hotel alert failed", admin_id=admin_id, error=str(exc))
