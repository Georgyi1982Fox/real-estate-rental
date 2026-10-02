"""Человек, который пишет боту в интеграционных тестах (несколько чатов сразу)."""

from datetime import UTC, datetime
from itertools import count
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import (
    CallbackQuery,
    Chat,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
    Update,
)
from aiogram.types import User as TelegramUser


class Person:
    """Человек пишет боту (арендатор или хозяин)."""

    def __init__(self, dispatcher: Dispatcher, bot: Bot, telegram_id: int, language: str) -> None:
        self.dispatcher = dispatcher
        self.bot = bot
        self.chat = Chat(id=telegram_id, type="private")
        self.user = TelegramUser(
            id=telegram_id, is_bot=False, first_name="User", language_code=language
        )
        self._ids = count(telegram_id * 1000)

    async def send(self, text: str) -> None:
        message = Message(
            message_id=next(self._ids),
            date=datetime.now(UTC),
            chat=self.chat,
            from_user=self.user,
            text=text,
        )
        await self.dispatcher.feed_update(
            self.bot, Update(update_id=next(self._ids), message=message)
        )

    async def press(self, data: str, markup: InlineKeyboardMarkup | None = None) -> None:
        message = Message(
            message_id=1, date=datetime.now(UTC), chat=self.chat, text="…", reply_markup=markup
        )
        query = CallbackQuery(
            id=str(next(self._ids)),
            from_user=self.user,
            chat_instance="ci",
            data=data,
            message=message,
        )
        await self.dispatcher.feed_update(
            self.bot, Update(update_id=next(self._ids), callback_query=query)
        )

    async def message(self, **content: Any) -> None:
        """Любое сообщение: фото, документ, оплата."""
        message = Message(
            message_id=next(self._ids),
            date=datetime.now(UTC),
            chat=self.chat,
            from_user=self.user,
            **content,
        )
        await self.dispatcher.feed_update(
            self.bot, Update(update_id=next(self._ids), message=message)
        )

    async def pre_checkout(self, payload: str, amount: int, currency: str = "XTR") -> None:
        query = PreCheckoutQuery(
            id=str(next(self._ids)),
            from_user=self.user,
            currency=currency,
            total_amount=amount,
            invoice_payload=payload,
        )
        await self.dispatcher.feed_update(
            self.bot, Update(update_id=next(self._ids), pre_checkout_query=query)
        )
