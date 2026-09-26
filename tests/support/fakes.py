"""In-memory реализации репозиториев для тестов бота и API."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.infrastructure.db.models import District, Listing, ListingStatus, User
from bina.infrastructure.db.models.users import SubscriptionTier, UserRole


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
