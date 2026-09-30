"""Защита бота от флуда (TASK-019).

Больше ``limit`` сообщений и нажатий за ``window`` секунд от одного человека —
лишние апдейты отбрасываются до обращения к базе. Предупреждение — один раз
за окно, на языке из Telegram.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware, Bot
from aiogram.dispatcher.middlewares.user_context import EVENT_FROM_USER_KEY
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser

from bina.infrastructure.bot.texts import t
from bina.infrastructure.ratelimit import SlidingWindowLimiter

logger = structlog.get_logger(__name__)

WINDOW_SECONDS = 10


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit: int, window: float = WINDOW_SECONDS) -> None:
        self._limiter = SlidingWindowLimiter(limit, window)
        # Кого уже предупредили — до какого момента окна (по часам лимитера)
        self._warned: SlidingWindowLimiter = SlidingWindowLimiter(1, window)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: TelegramUser | None = data.get(EVENT_FROM_USER_KEY)
        if user is None:
            return await handler(event, data)
        key = str(user.id)
        if self._limiter.hit(key) is None:
            return await handler(event, data)
        logger.info("Update throttled", telegram_id=user.id)
        bot: Bot | None = data.get("bot")
        if bot is not None and self._warned.hit(key) is None:
            try:
                await bot.send_message(user.id, t(user.language_code or "", "too_fast"))
            except Exception as exc:  # noqa: BLE001 - предупреждение не обязательно
                logger.info("Throttle warning not sent", error=str(exc))
        return None
