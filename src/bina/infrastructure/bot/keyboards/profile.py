"""Клавиатура профиля: выбор языка."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bina.application.use_cases.register_user import SUPPORTED_LANGUAGES
from src.bina.infrastructure.bot.keyboards.callbacks import LanguageCallback
from src.bina.infrastructure.bot.texts import LANGUAGE_NAMES


def language_keyboard(current: str) -> InlineKeyboardMarkup:
    """Кнопки языков; текущий отмечен галочкой."""
    builder = InlineKeyboardBuilder()
    for code in sorted(SUPPORTED_LANGUAGES, key=list(LANGUAGE_NAMES).index):
        mark = "✅ " if code == current else ""
        builder.button(
            text=f"{mark}{LANGUAGE_NAMES[code]}",
            callback_data=LanguageCallback(code=code),
        )
    builder.adjust(len(SUPPORTED_LANGUAGES))
    return builder.as_markup()
