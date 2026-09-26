"""Фикстуры тестов REST API: приложение поверх in-memory репозиториев."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.api import dependencies
from bina.infrastructure.api.routes import common, districts, favorites, listings
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from tests.support.fakes import (
    FakeDistrictsRepository,
    FakeFavoritesRepository,
    FakeListingsRepository,
    FakeUsersRepository,
    Store,
)
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
ORIGIN = "https://georgyi1982fox.github.io"
TELEGRAM_USER = {"id": 555, "first_name": "Nino", "language_code": "en"}


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Store:
    """In-memory «база», подставленная во все модули API."""
    store = Store()

    def fake(cls: type) -> Callable[[AsyncSession], Any]:
        return lambda session: cls(store)

    monkeypatch.setattr(dependencies, "UsersRepository", fake(FakeUsersRepository))
    monkeypatch.setattr(common, "ListingsRepository", fake(FakeListingsRepository))
    monkeypatch.setattr(listings, "ListingsRepository", fake(FakeListingsRepository))
    monkeypatch.setattr(districts, "DistrictsRepository", fake(FakeDistrictsRepository))
    monkeypatch.setattr(favorites, "ListingsRepository", fake(FakeListingsRepository))
    monkeypatch.setattr(favorites, "FavoritesRepository", fake(FakeFavoritesRepository))
    return store


@pytest.fixture
def sessions() -> list[AsyncMock]:
    """Сессии БД, открытые за время теста (для проверки commit)."""
    return []


@pytest.fixture
def settings() -> ApiSettings:
    """Настройки API для тестов."""
    return ApiSettings(bot_token=BOT_TOKEN)


@pytest.fixture
async def client(
    store: Store,
    settings: ApiSettings,
    sessions: list[AsyncMock],
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент к приложению (без сети)."""

    @asynccontextmanager
    async def session_factory() -> AsyncIterator[AsyncMock]:
        session = AsyncMock(spec=AsyncSession)
        sessions.append(session)
        yield session

    app = create_app(settings, cast(async_sessionmaker[AsyncSession], session_factory))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
def auth() -> dict[str, str]:
    """Заголовок с корректно подписанным initData."""
    return {"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, TELEGRAM_USER)}
