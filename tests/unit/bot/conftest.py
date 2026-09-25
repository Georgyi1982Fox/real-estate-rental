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
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

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

from src.bina.application.dtos.listing_search import ListingSearchFilters
from src.bina.infrastructure.bot import factory as bot_factory
from src.bina.infrastructure.bot.handlers import favorites as favorites_handlers
from src.bina.infrastructure.bot.handlers import profile as profile_handlers
from src.bina.infrastructure.bot.handlers import search as search_handlers
from src.bina.infrastructure.bot.middlewares import registration
from src.bina.infrastructure.bot.settings import BotSettings
from src.bina.infrastructure.db.models import District, Listing, ListingStatus, User
from src.bina.infrastructure.db.models.users import SubscriptionTier, UserRole
from tests.support.telegram import CHAT_ID, TOKEN, FakeTelegramSession

# --------------------------------------------------------------------------- store


@dataclass
class Store:
    """In-memory «база данных» для тестов."""

    users: dict[int, User] = field(default_factory=dict)
    districts: list[District] = field(default_factory=list)
    listings: list[Listing] = field(default_factory=list)
    favorites: list[tuple[UUID, UUID]] = field(default_factory=list)

    def add_district(self, name_ru: str, name_en: str = "", name_ka: str = "") -> District:
        """Добавить район."""
        district = District(
            id=uuid4(),
            name_ru=name_ru,
            name_en=name_en or name_ru,
            name_ka=name_ka or name_ru,
            avg_price_per_m2=Decimal(10),
            safety_score=5,
            is_deleted=False,
        )
        self.districts.append(district)
        return district

    def add_listing(
        self,
        district: District,
        price: int = 1000,
        rooms: int = 2,
        title_ru: str = "Квартира",
        **kwargs: Any,
    ) -> Listing:
        """Добавить объявление (каждое следующее новее предыдущего)."""
        listing = Listing(
            id=uuid4(),
            source_id=str(uuid4()),
            source_name="test",
            title_ru=title_ru,
            title_ka=kwargs.pop("title_ka", "ბინა"),
            description_ru="",
            description_ka="",
            price=Decimal(price),
            currency=kwargs.pop("currency", "GEL"),
            district_id=district.id,
            rooms=rooms,
            area=Decimal(kwargs.pop("area", 50)),
            is_verified=kwargs.pop("is_verified", False),
            fraud_score=0,
            status=kwargs.pop("status", ListingStatus.ACTIVE),
            is_deleted=kwargs.pop("is_deleted", False),
            created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=len(self.listings)),
        )
        assert not kwargs, f"unexpected kwargs: {kwargs}"
        self.listings.append(listing)
        return listing

    def listing(self, listing_id: UUID) -> Listing | None:
        """Найти объявление по ID."""
        return next((item for item in self.listings if item.id == listing_id), None)


class FakeUsersRepository:
    """In-memory :class:`IUsersRepository`."""

    def __init__(self, store: Store) -> None:
        self._store = store

    async def get_by_id(self, user_id: UUID) -> User | None:
        return next((u for u in self._store.users.values() if u.id == user_id), None)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return self._store.users.get(telegram_id)

    async def create(self, telegram_id: int, language: str) -> User:
        user = User(
            id=uuid4(),
            telegram_id=telegram_id,
            language=language,
            role=UserRole.USER,
            balance=Decimal(0),
            subscription_tier=SubscriptionTier.FREE,
            subscription_expires_at=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
            is_deleted=False,
        )
        self._store.users[telegram_id] = user
        return user

    async def update_language(self, user_id: UUID, language: str) -> None:
        user = await self.get_by_id(user_id)
        assert user is not None
        user.language = language


class FakeDistrictsRepository:
    """In-memory часть :class:`IDistrictsRepository`, нужная боту."""

    def __init__(self, store: Store) -> None:
        self._store = store

    async def get_by_id(self, district_id: UUID) -> District | None:
        return next((d for d in self._store.districts if d.id == district_id), None)

    async def list_all(self) -> list[District]:
        return sorted(self._store.districts, key=lambda d: d.name_ru)


class FakeListingsRepository:
    """In-memory часть :class:`IListingsRepository`, нужная боту."""

    def __init__(self, store: Store) -> None:
        self._store = store

    def _matching(self, f: ListingSearchFilters) -> list[Listing]:
        result = [
            item
            for item in self._store.listings
            if item.status == ListingStatus.ACTIVE
            and not item.is_deleted
            and (f.district_id is None or item.district_id == f.district_id)
            and (f.price_min is None or item.price >= f.price_min)
            and (f.price_max is None or item.price <= f.price_max)
            and (f.rooms_min is None or item.rooms >= f.rooms_min)
            and (f.rooms_max is None or item.rooms <= f.rooms_max)
        ]
        return sorted(result, key=lambda item: item.created_at, reverse=True)

    async def search(
        self, filters: ListingSearchFilters, limit: int, offset: int = 0
    ) -> list[Listing]:
        return self._matching(filters)[offset : offset + limit]

    async def count(self, filters: ListingSearchFilters) -> int:
        return len(self._matching(filters))

    async def get_by_id(self, listing_id: UUID) -> Listing | None:
        return self._store.listing(listing_id)


class FakeFavoritesRepository:
    """In-memory :class:`IFavoritesRepository`."""

    def __init__(self, store: Store) -> None:
        self._store = store

    async def add(self, user_id: UUID, listing_id: UUID) -> None:
        if (user_id, listing_id) not in self._store.favorites:
            self._store.favorites.append((user_id, listing_id))

    async def remove(self, user_id: UUID, listing_id: UUID) -> bool:
        if (user_id, listing_id) in self._store.favorites:
            self._store.favorites.remove((user_id, listing_id))
            return True
        return False

    async def exists(self, user_id: UUID, listing_id: UUID) -> bool:
        return (user_id, listing_id) in self._store.favorites

    async def filter_favorite_ids(self, user_id: UUID, listing_ids: Any) -> set[UUID]:
        return {lid for uid, lid in self._store.favorites if uid == user_id and lid in listing_ids}

    async def list_by_user(self, user_id: UUID, limit: int, offset: int = 0) -> list[Listing]:
        return self._user_listings(user_id)[offset : offset + limit]

    async def count_by_user(self, user_id: UUID) -> int:
        return len(self._user_listings(user_id))

    def _user_listings(self, user_id: UUID) -> list[Listing]:
        result = []
        for uid, lid in reversed(self._store.favorites):
            listing = self._store.listing(lid)
            if uid == user_id and listing is not None and not listing.is_deleted:
                result.append(listing)
        return result


# --------------------------------------------------------------------------- telegram


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
