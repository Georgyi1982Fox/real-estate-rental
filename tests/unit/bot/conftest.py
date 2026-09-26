"""Фикстуры для тестов бота.

Бот прогоняется через настоящий :class:`Dispatcher` (роутеры, фильтры,
middleware), но без сети и без БД:

- Telegram API заменён :class:`FakeTelegramSession`, которая записывает вызовы;
- репозитории заменены in-memory реализациями поверх :class:`Store`;
- сессия БД это ``AsyncMock``, по ней проверяются commit/rollback.
"""

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import count
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import (
    CallbackQuery,
    Chat,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.bot import factory as bot_factory
from bina.infrastructure.bot.handlers import favorites as favorites_handlers
from bina.infrastructure.bot.handlers import profile as profile_handlers
from bina.infrastructure.bot.handlers import search as search_handlers
from bina.infrastructure.bot.middlewares import registration
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.db.models import User
from tests.support.fakes import (
    FakeDistrictsRepository,
    FakeFavoritesRepository,
    FakeListingsRepository,
    FakeUsersRepository,
    Store,
)
from tests.support.telegram import CHAT_ID, TOKEN, FakeTelegramSession

# --------------------------------------------------------------------------- harness


@dataclass
class BotHarness:
    """Бот + фейковый Telegram + in-memory БД."""

    dispatcher: Dispatcher
    bot: Bot
    telegram: FakeTelegramSession
    store: Store
    sessions: list[AsyncMock]
    telegram_user: TelegramUser
    _ids: Iterator[int] = field(default_factory=lambda: count(1))

    async def send(self, text: str, **user: Any) -> None:
        """Пользователь пишет сообщение."""
        from_user = self.telegram_user.model_copy(update=user)
        await self.dispatcher.feed_update(
            self.bot,
            Update(
                update_id=next(self._ids),
                message=Message(
                    message_id=next(self._ids),
                    date=datetime.now(UTC),
                    chat=Chat(id=CHAT_ID, type="private"),
                    from_user=from_user,
                    text=text,
                ),
            ),
        )

    async def press(
        self,
        data: str,
        markup: InlineKeyboardMarkup | None = None,
        message: Any = None,
    ) -> None:
        """Пользователь нажимает inline-кнопку под сообщением с ``markup``."""
        if message is None:
            message = Message(
                message_id=500,
                date=datetime.now(UTC),
                chat=Chat(id=CHAT_ID, type="private"),
                text="…",
                reply_markup=markup,
            )
        await self.dispatcher.feed_update(
            self.bot,
            Update(
                update_id=next(self._ids),
                callback_query=CallbackQuery(
                    id=str(next(self._ids)),
                    from_user=self.telegram_user,
                    chat_instance="ci",
                    data=data,
                    message=message,
                ),
            ),
        )

    @property
    def user(self) -> User:
        """Зарегистрированный пользователь теста."""
        return self.store.users[self.telegram_user.id]

    def last_text(self) -> str:
        """Текст последнего отправленного или отредактированного сообщения."""
        for call in reversed(self.telegram.calls):
            if isinstance(call, SendMessage | EditMessageText):
                return call.text or ""
        raise AssertionError("no messages were sent")

    def last_markup(self) -> Any:
        """Клавиатура последнего отправленного или отредактированного сообщения."""
        for call in reversed(self.telegram.calls):
            if isinstance(call, SendMessage | EditMessageText):
                return call.reply_markup
        raise AssertionError("no messages were sent")

    def reset(self) -> None:
        """Забыть записанные вызовы API."""
        self.telegram.calls.clear()


@pytest.fixture
def store() -> Store:
    """Пустое in-memory хранилище."""
    return Store()


@pytest.fixture
def settings() -> BotSettings:
    """Настройки бота для тестов."""
    return BotSettings(token=TOKEN, page_size=3)


@pytest.fixture
def patch_repositories(monkeypatch: pytest.MonkeyPatch, store: Store) -> None:
    """Подменяет репозитории в модулях бота in-memory реализациями."""

    def fake(cls: type) -> Callable[[AsyncSession], Any]:
        return lambda session: cls(store)

    monkeypatch.setattr(registration, "UsersRepository", fake(FakeUsersRepository))
    monkeypatch.setattr(search_handlers, "DistrictsRepository", fake(FakeDistrictsRepository))
    monkeypatch.setattr(search_handlers, "ListingsRepository", fake(FakeListingsRepository))
    monkeypatch.setattr(search_handlers, "FavoritesRepository", fake(FakeFavoritesRepository))
    monkeypatch.setattr(favorites_handlers, "ListingsRepository", fake(FakeListingsRepository))
    monkeypatch.setattr(favorites_handlers, "FavoritesRepository", fake(FakeFavoritesRepository))
    monkeypatch.setattr(profile_handlers, "UsersRepository", fake(FakeUsersRepository))
    monkeypatch.setattr(profile_handlers, "FavoritesRepository", fake(FakeFavoritesRepository))


@pytest.fixture
def harness(
    patch_repositories: None,
    store: Store,
    settings: BotSettings,
) -> BotHarness:
    """Собранный бот, готовый принимать апдейты."""
    sessions: list[AsyncMock] = []

    @asynccontextmanager
    async def session_factory() -> AsyncIterator[AsyncMock]:
        session = AsyncMock(spec=AsyncSession)
        sessions.append(session)
        yield session

    telegram = FakeTelegramSession()
    dispatcher = bot_factory.create_dispatcher(
        settings,
        cast(async_sessionmaker[AsyncSession], session_factory),
    )
    return BotHarness(
        dispatcher=dispatcher,
        bot=Bot(token=TOKEN, session=telegram),
        telegram=telegram,
        store=store,
        sessions=sessions,
        telegram_user=TelegramUser(
            id=CHAT_ID, is_bot=False, first_name="Nino", language_code="ru"
        ),
    )
