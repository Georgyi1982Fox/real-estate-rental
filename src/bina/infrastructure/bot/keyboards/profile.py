"""Клавиатура профиля: выбор языка и свои данные."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bina.application.use_cases.register_user import SUPPORTED_LANGUAGES
from bina.infrastructure.bot.keyboards.callbacks import (
    AccountAction,
    AccountCallback,
    LanguageCallback,
)
from bina.infrastructure.bot.texts import LANGUAGE_NAMES, t


def language_keyboard(current: str) -> InlineKeyboardMarkup:
    """Кнопки языков (текущий отмечен галочкой); ниже — скачать и удалить свои данные."""
    builder = InlineKeyboardBuilder()
    for code in sorted(SUPPORTED_LANGUAGES, key=list(LANGUAGE_NAMES).index):
        mark = "✅ " if code == current else ""
        builder.button(
            text=f"{mark}{LANGUAGE_NAMES[code]}",
            callback_data=LanguageCallback(code=code),
        )
    builder.button(
        text=t(current, "account_export"),
        callback_data=AccountCallback(action=AccountAction.EXPORT),
    )
    builder.button(
        text=t(current, "account_delete"),
        callback_data=AccountCallback(action=AccountAction.ASK_DELETE),
    )
    builder.adjust(len(SUPPORTED_LANGUAGES), 1, 1)
    return builder.as_markup()


def delete_confirm_keyboard(language: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t(language, "account_delete_yes"),
        callback_data=AccountCallback(action=AccountAction.DELETE),
    )
    builder.button(
        text=t(language, "account_delete_no"),
        callback_data=AccountCallback(action=AccountAction.CANCEL),
    )
    builder.adjust(1)
    return builder.as_markup()
