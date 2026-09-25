"""Общие утилиты обработчиков."""

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bina.infrastructure.bot.texts import t


async def edit_or_answer(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
    language: str,
) -> None:
    """Редактирует сообщение с кнопкой; если оно недоступно, предлагает открыть раздел заново.

    Ошибку Telegram «message is not modified» (повторное нажатие той же кнопки)
    игнорирует.
    """
    if not isinstance(callback.message, Message):
        await callback.answer(t(language, "message_outdated"), show_alert=True)
        return
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise
    await callback.answer()
