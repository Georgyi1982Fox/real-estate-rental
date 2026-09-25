from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.dispatcher.middlewares.user_context import EVENT_FROM_USER_KEY
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.bot.middlewares import (
    DbSessionMiddleware,
    RegistrationMiddleware,
    registration,
)

from .conftest import FakeUsersRepository, Store

EVENT = cast(TelegramObject, MagicMock())


def session_factory(session: AsyncMock) -> async_sessionmaker[AsyncSession]:
    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncMock]:
        yield session

    return cast(async_sessionmaker[AsyncSession], factory)


async def test_db_session_commits_on_success() -> None:
    session = AsyncMock(spec=AsyncSession)
    handler = AsyncMock(return_value="ok")
    data: dict[str, Any] = {}

    result = await DbSessionMiddleware(session_factory(session))(handler, EVENT, data)

    assert result == "ok"
    assert data["session"] is session
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


async def test_db_session_rolls_back_on_error() -> None:
    session = AsyncMock(spec=AsyncSession)
    handler = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        await DbSessionMiddleware(session_factory(session))(handler, EVENT, {})

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Store:
    store = Store()
    monkeypatch.setattr(registration, "UsersRepository", lambda session: FakeUsersRepository(store))
    return store


def tg_user(**overrides: Any) -> TelegramUser:
    values: dict[str, Any] = {"id": 1, "is_bot": False, "first_name": "A", "language_code": "en"}
    values.update(overrides)
    return TelegramUser(**values)


async def test_registration_creates_user_and_passes_it(store: Store) -> None:
    handler = AsyncMock()
    data: dict[str, Any] = {EVENT_FROM_USER_KEY: tg_user(), "session": AsyncMock()}

    await RegistrationMiddleware()(handler, EVENT, data)

    handler.assert_awaited_once()
    assert data["user"] is store.users[1]
    assert data["is_new_user"] is True
    assert data["user_language"] == "en"


async def test_registration_reuses_existing_user(store: Store) -> None:
    data: dict[str, Any] = {EVENT_FROM_USER_KEY: tg_user(), "session": AsyncMock()}
    await RegistrationMiddleware()(AsyncMock(), EVENT, data)
    first = data["user"]

    data = {EVENT_FROM_USER_KEY: tg_user(language_code="ru"), "session": AsyncMock()}
    await RegistrationMiddleware()(AsyncMock(), EVENT, data)

    assert data["user"] is first
    assert data["is_new_user"] is False
    assert data["user_language"] == "en", "язык из профиля не перезаписывается"


@pytest.mark.parametrize("from_user", [None, tg_user(is_bot=True)])
async def test_registration_drops_updates_without_human(
    store: Store,
    from_user: TelegramUser | None,
) -> None:
    handler = AsyncMock()

    result = await RegistrationMiddleware()(
        handler, EVENT, {EVENT_FROM_USER_KEY: from_user, "session": AsyncMock()}
    )

    assert result is None
    handler.assert_not_awaited()
    assert store.users == {}
