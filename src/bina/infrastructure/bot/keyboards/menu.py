"""Главное меню и общие кнопки."""

from aiogram.types import (
    InlineKeyboardButton,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from bina.infrastructure.bot.texts import t


def main_menu(language: str) -> ReplyKeyboardMarkup:
    """Постоянная клавиатура главного меню."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(language, "menu_search"))],
            [
                KeyboardButton(text=t(language, "menu_favorites")),
                KeyboardButton(text=t(language, "menu_profile")),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def open_app_button(language: str, mini_app_url: str) -> InlineKeyboardButton:
    """Кнопка открытия Telegram Mini App."""
    return InlineKeyboardButton(
        text=t(language, "open_app"),
        web_app=WebAppInfo(url=mini_app_url),
    )
