"""Сообщение владельцу сервиса о новом объявлении собственника (TASK-096).

Объявление сразу в поиске; владелец видит его в Telegram и может скрыть одной
кнопкой (та же, что в админке для жалоб). Используется ботом и API Mini App.
"""

from collections.abc import Iterable
from html import escape
from uuid import UUID

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bina.infrastructure.bot.formatters import format_listing
from bina.infrastructure.bot.keyboards.callbacks import AdminAction, AdminCallback
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import Listing, User

logger = structlog.get_logger(__name__)

# Столько знаков описания в сообщении владельцу
DESCRIPTION_PREVIEW = 300


async def notify_admins(bot: Bot, admin_ids: Iterable[int], listing: Listing, author: User) -> None:
    """Каждому админу — карточка, начало описания и кнопка «Скрыть»."""
    for admin_id in admin_ids:
        # Свой язык — если админ разместил сам; иначе русский (язык владельца)
        language = author.language if author.telegram_id == admin_id else "ru"
        try:
            await bot.send_message(
                admin_id,
                t(
                    language,
                    "owner_admin_new",
                    listing=format_listing(listing, 1, language),
                    photos=len(listing.images or []),
                    description=escape(_description(listing)[:DESCRIPTION_PREVIEW]),
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[_hide_button(language, listing.id)]]
                ),
            )
        except TelegramAPIError as exc:
            # Сообщение владельцу не должно ломать размещение
            logger.warning("Owner listing alert failed", admin_id=admin_id, error=str(exc))


def _description(listing: Listing) -> str:
    return listing.description_ru or listing.description_ka or listing.description_en or ""


def _hide_button(language: str, listing_id: UUID) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=t(language, "owner_admin_hide"),
        callback_data=AdminCallback(action=AdminAction.HIDE, listing=listing_id).pack(),
    )
