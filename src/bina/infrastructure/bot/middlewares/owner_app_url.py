"""Владельцу — свой адрес Mini App во всех кнопках бота (TASK-124).

Провайдер владельца может не пускать к основному адресу (Cloudflare), а у остальных
людей он открывается. Тогда в ``.env`` задают ``BOT_OWNER_MINI_APP_URL`` (например,
российский туннель), и для сообщений владельца обработчики получают ``settings``
с этим адресом вместо ``BOT_MINI_APP_URL``.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.dispatcher.middlewares.user_context import EVENT_FROM_USER_KEY
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser

from bina.infrastructure.bot.settings import BotSettings


class OwnerAppUrlMiddleware(BaseMiddleware):
    """Подменяет ``settings`` на :meth:`BotSettings.for_user` автора апдейта."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        settings = data.get("settings")
        user = data.get(EVENT_FROM_USER_KEY)
        if isinstance(settings, BotSettings) and isinstance(user, TelegramUser):
            data["settings"] = settings.for_user(user.id)
        return await handler(event, data)
