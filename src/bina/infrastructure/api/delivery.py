"""Выдача PDF-документов (договор, акт приёмки): в чат с ботом или файлом в ответе.

- ``delivery=chat`` (по умолчанию) — бот присылает PDF в чат с пользователем:
  из Mini App так проще всего сохранить и переслать файл.
- ``delivery=file`` — PDF в ответе (для браузера и проверки).
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile
from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel

from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User

# sign — сохранить на подпись (TASK-115): договор и акт, см. routes/documents.py
Delivery = Literal["chat", "file", "sign"]

# Название второго языка документа — на языке пользователя
LANGUAGE_NAMES = {
    "ru": {"ru": "русский", "en": "английский"},
    "en": {"ru": "Russian", "en": "English"},
    "ka": {"ru": "რუსული", "en": "ინგლისური"},
}
SECOND_LANGUAGES = ("ru", "en")


class DocumentSentOut(BaseModel):
    """Документ отправлен в чат."""

    sent: bool
    filename: str


class DocumentSender(Protocol):
    """Отправка файла пользователю в Telegram (в тестах — подмена)."""

    async def __call__(self, chat_id: int, filename: str, content: bytes, caption: str) -> None: ...


@dataclass(frozen=True, slots=True)
class BotDocumentSender:
    """Отправка через Bot API ``sendDocument``."""

    bot_token: str

    async def __call__(self, chat_id: int, filename: str, content: bytes, caption: str) -> None:
        bot = Bot(token=self.bot_token)
        try:
            await bot.send_document(
                chat_id, BufferedInputFile(content, filename=filename), caption=caption
            )
        finally:
            await bot.session.close()


def ui_language(user: User) -> str:
    """Язык подписей: язык пользователя (ka / ru / en), иначе английский."""
    return user.language if user.language in LANGUAGE_NAMES else "en"


def viewer_language(user: User | None, lang: str | None) -> str:
    """Язык для вошедшего — его, для гостя сайта — ``lang`` из запроса (по умолчанию ru)."""
    if user is not None:
        return ui_language(user)
    return lang if lang in LANGUAGE_NAMES else "ru"


def second_language(user: User, chosen: str | None) -> str:
    """Второй язык документа (первый — грузинский): выбранный или язык пользователя."""
    if chosen:
        return chosen
    return user.language if user.language in SECOND_LANGUAGES else "en"


def _sender(request: Request, settings: ApiSettings) -> DocumentSender:
    injected: DocumentSender | None = getattr(request.app.state, "document_sender", None)
    if injected is not None:
        return injected
    if not settings.bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bot is not configured"
        )
    return BotDocumentSender(settings.bot_token)


async def deliver_pdf(
    request: Request,
    settings: ApiSettings,
    user: User,
    *,
    pdf: bytes,
    filename: str,
    caption: str,
    delivery: Delivery,
) -> DocumentSentOut | Response:
    """PDF файлом в ответе или сообщением от бота."""
    if delivery == "file":
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    try:
        await _sender(request, settings)(user.telegram_id, filename, pdf, caption)
    except TelegramAPIError as exc:
        # Например, пользователь не запускал бота или заблокировал его
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not send the file to the chat"
        ) from exc
    return DocumentSentOut(sent=True, filename=filename)
