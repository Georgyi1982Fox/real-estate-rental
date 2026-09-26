"""Зависимости FastAPI: сессия БД, настройки, текущий пользователь."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.use_cases.register_user import RegisterUserUseCase
from bina.infrastructure.api.auth import INIT_DATA_HEADER, resolve_identity
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.users import UsersRepository


def get_settings(request: Request) -> ApiSettings:
    """Настройки приложения (``app.state.settings``)."""
    settings: ApiSettings = request.app.state.settings
    return settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Сессия БД на запрос.

    Изменения фиксирует сам эндпоинт (``await session.commit()``); всё
    незафиксированное откатывается при закрытии сессии.
    """
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[ApiSettings, Depends(get_settings)]


async def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    init_data: Annotated[str | None, Header(alias=INIT_DATA_HEADER)] = None,
    user_id: Annotated[
        int | None,
        Query(description="Telegram ID; должен совпадать с X-Telegram-Init-Data"),
    ] = None,
) -> User:
    """Пользователь запроса; регистрируется при первом обращении из Mini App."""
    identity = resolve_identity(settings, init_data, user_id)
    result = await RegisterUserUseCase(UsersRepository(session)).execute(
        telegram_id=identity.telegram_id,
        language_code=identity.language_code,
    )
    if result.created:
        await session.commit()
    return result.user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
