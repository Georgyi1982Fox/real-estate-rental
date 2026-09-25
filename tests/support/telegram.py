"""Фейковый Telegram Bot API для тестов бота."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from itertools import count
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText, SendMessage, TelegramMethod
from aiogram.types import Chat, InlineKeyboardMarkup, Message

TOKEN = "42:TEST"
CHAT_ID = 777


class FakeTelegramSession(BaseSession):
    """Сессия aiogram, которая не ходит в сеть, а записывает вызовы API."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.fail_edit_with: str | None = None
        self._ids = count(1000)

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,
    ) -> Any:
        self.calls.append(method)
        if isinstance(method, EditMessageText) and self.fail_edit_with:
            raise TelegramBadRequest(method=method, message=self.fail_edit_with)
        if isinstance(method, SendMessage):
            markup = method.reply_markup
            return Message(
                message_id=next(self._ids),
                date=datetime.now(UTC),
                chat=Chat(id=CHAT_ID, type="private"),
                text=method.text,
                reply_markup=markup if isinstance(markup, InlineKeyboardMarkup) else None,
            )
        return True

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        yield b""  # pragma: no cover

    async def close(self) -> None:
        pass

    def of(self, method_type: type[TelegramMethod[Any]]) -> list[Any]:
        """Вызовы API заданного типа."""
        return [call for call in self.calls if isinstance(call, method_type)]
