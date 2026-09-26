"""Фейковый Telegram Bot API и подпись initData для тестов."""

import hashlib
import hmac
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from itertools import count
from typing import Any
from urllib.parse import urlencode

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


def sign_init_data(
    token: str,
    user: dict[str, Any] | None,
    auth_date: datetime | None = None,
) -> str:
    """Строка ``Telegram.WebApp.initData``, подписанная как это делает Telegram."""
    fields = {
        "auth_date": str(int((auth_date or datetime.now(UTC)).timestamp())),
        "query_id": "AAHtest",
    }
    if user is not None:
        fields["user"] = json.dumps(user, separators=(",", ":"))
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)
