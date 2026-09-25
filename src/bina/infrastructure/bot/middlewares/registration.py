from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.dispatcher.middlewares.user_context import EVENT_FROM_USER_KEY
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from src.bina.application.use_cases.register_user import RegisterUserUseCase
from src.bina.infrastructure.db.repositories.users import UsersRepository

logger = structlog.get_logger(__name__)


class RegistrationMiddleware(BaseMiddleware):
    """Гарантирует, что отправитель апдейта зарегистрирован.

    Кладёт в ``data``:

    - ``user``: модель :class:`User` из БД;
    - ``is_new_user``: ``True``, если пользователь создан этим апдейтом;
    - ``user_language``: язык пользователя строкой. Нужен обработчику ошибок:
      после rollback атрибуты ``user`` недоступны (объект expired и detached).

    Апдейты без отправителя-человека (посты каналов, анонимные админы групп,
    другие боты) отбрасываются: все обработчики бота рассчитаны на
    зарегистрированного пользователя. Должен регистрироваться после
    :class:`DbSessionMiddleware`.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Регистрирует пользователя и передаёт его обработчику."""
        telegram_user: TelegramUser | None = data.get(EVENT_FROM_USER_KEY)
        if telegram_user is None or telegram_user.is_bot:
            return None

        session: AsyncSession = data["session"]
        result = await RegisterUserUseCase(UsersRepository(session)).execute(
            telegram_id=telegram_user.id,
            language_code=telegram_user.language_code,
        )
        data["user"] = result.user
        data["is_new_user"] = result.created
        data["user_language"] = result.user.language
        return await handler(event, data)
