"""In-memory реализации репозиториев для тестов бота и API."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from bina.application.dtos.listing_search import ListingSearchFilters, ListingSort
from bina.application.fraud import HIDE_SCORE
from bina.application.referrals import CODE_ALPHABET
from bina.infrastructure.db.models import District, Listing, ListingStatus, User
from bina.infrastructure.db.models.users import SubscriptionTier, UserRole


@dataclass
class Store:
    """In-memory «база данных» для тестов."""

    users: dict[int, User] = field(default_factory=dict)
    districts: list[District] = field(default_factory=list)
    listings: list[Listing] = field(default_factory=list)
    favorites: list[tuple[UUID, UUID]] = field(default_factory=list)
    # (user_id, charge_id, amount, plan)
    payments: list[tuple[UUID, str, Decimal, str]] = field(default_factory=list)
    # Служебные уведомления: (user_id, тексты по языкам)
    notifications: list[tuple[UUID, dict[str, str]]] = field(default_factory=list)
    rent_reminders: list[Any] = field(default_factory=list)

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
            title_en=kwargs.pop("title_en", ""),
            description_en=kwargs.pop("description_en", ""),
            price=Decimal(price),
            currency=kwargs.pop("currency", "GEL"),
            district_id=district.id,
            rooms=rooms,
            area=Decimal(kwargs.pop("area", 50)),
            images=kwargs.pop("images", []),
            url=kwargs.pop("url", None),
            phone=kwargs.pop("phone", None),
            owner_name=kwargs.pop("owner_name", None),
            is_verified=kwargs.pop("is_verified", False),
            fraud_score=kwargs.pop("fraud_score", 0),
            fraud_reasons=kwargs.pop("fraud_reasons", []),
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

    async def set_subscription(
        self, user_id: UUID, tier: SubscriptionTier, expires_at: datetime
    ) -> None:
        user = await self.get_by_id(user_id)
        assert user is not None
        user.subscription_tier = tier
        user.subscription_expires_at = expires_at


class FakePaymentsRepository:
    """In-memory :class:`IPaymentsRepository`."""

    def __init__(self, store: Store) -> None:
        self._store = store

    async def exists(self, provider_payment_id: str) -> bool:
        return any(item[1] == provider_payment_id for item in self._store.payments)

    async def add_success(
        self,
        user_id: UUID,
        amount: Decimal,
        currency: str,
        provider_payment_id: str,
        plan: str,
    ) -> None:
        self._store.payments.append((user_id, provider_payment_id, amount, plan))


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
            and item.fraud_score < HIDE_SCORE
            and (not f.all_district_ids or item.district_id in f.all_district_ids)
            and (f.price_min is None or item.price >= f.price_min)
            and (f.price_max is None or item.price <= f.price_max)
            and (f.rooms_min is None or item.rooms >= f.rooms_min)
            and (f.rooms_max is None or item.rooms <= f.rooms_max)
            and (f.area_min is None or item.area >= f.area_min)
            and (f.area_max is None or item.area <= f.area_max)
            and (f.query is None or _matches_text(item, f.query))
        ]
        return sorted(result, key=lambda item: item.created_at, reverse=True)

    async def search(
        self,
        filters: ListingSearchFilters,
        limit: int,
        offset: int = 0,
        sort: ListingSort = ListingSort.NEWEST,
    ) -> list[Listing]:
        items = self._matching(filters)  # уже новые сверху; sorted() устойчива
        keys: dict[ListingSort, Any] = {
            ListingSort.PRICE_ASC: lambda item: item.price,
            ListingSort.PRICE_DESC: lambda item: -item.price,
            ListingSort.AREA_DESC: lambda item: -item.area,
            ListingSort.PRICE_PER_M2_ASC: lambda item: item.price / item.area,
        }
        if sort in keys:
            items = sorted(items, key=keys[sort])
        return items[offset : offset + limit]

    async def count(self, filters: ListingSearchFilters) -> int:
        return len(self._matching(filters))

    async def same_apartment_links(self, listing: Listing) -> list[tuple[str, str]]:
        return [(listing.source_name, listing.url)] if listing.url else []

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

    async def list_ids(self, user_id: UUID, limit: int) -> list[UUID]:
        return [listing.id for listing in self._user_listings(user_id)][:limit]

    def _user_listings(self, user_id: UUID) -> list[Listing]:
        result = []
        for uid, lid in reversed(self._store.favorites):
            listing = self._store.listing(lid)
            if uid == user_id and listing is not None and not listing.is_deleted:
                result.append(listing)
        return result


# --------------------------------------------------------------------------- telegram


def _matches_text(listing: Listing, query: str) -> bool:
    """Упрощённый аналог полнотекстового поиска: каждое слово — начало слова в тексте."""
    text = " ".join(
        str(getattr(listing, f"{field}_{code}", "") or "")
        for field in ("title", "description")
        for code in ("ru", "ka", "en")
    ).lower()
    words = re.findall(r"\w+", text)
    return all(
        any(word.startswith(part) for word in words) for part in re.findall(r"\w+", query.lower())
    )


class FakeReferralsRepository:
    """In-memory приглашения (TASK-108): коды и связи хранятся в моделях :class:`User`."""

    def __init__(self, store: Store) -> None:
        self._store = store

    def _users(self) -> list[User]:
        return list(self._store.users.values())

    async def code_for(self, user: User) -> str:
        if not user.referral_code:
            # Код из допустимых символов: «frndxy» + 2 знака по номеру пользователя
            index = len([u for u in self._users() if u.referral_code])
            user.referral_code = "frndxy" + CODE_ALPHABET[index] * 2
        return user.referral_code

    async def by_code(self, code: str) -> User | None:
        return next((u for u in self._users() if u.referral_code == code), None)

    async def set_referrer(self, user: User, referrer: User) -> bool:
        if referrer.id == user.id or user.referred_by is not None or await self.paid_count(user.id):
            return False
        user.referred_by = referrer.id
        return True

    async def discount_eligible(self, user: User) -> bool:
        return user.referred_by is not None and await self.paid_count(user.id) == 0

    async def stats(self, user_id: UUID, since: datetime) -> tuple[int, int, int]:
        friends = [u for u in self._users() if u.referred_by == user_id]
        rewarded = [u for u in friends if u.referral_rewarded_at is not None]
        recent = [u for u in rewarded if u.referral_rewarded_at and u.referral_rewarded_at >= since]
        return len(friends), len(rewarded), len(recent)

    async def friend(self, user_id: UUID) -> Any:
        from bina.application.use_cases.referrals import Friend

        user = next(u for u in self._users() if u.id == user_id)
        return Friend(
            user_id=user_id,
            referred_by=user.referred_by,
            rewarded=user.referral_rewarded_at is not None,
        )

    async def paid_count(self, user_id: UUID) -> int:
        return sum(1 for item in self._store.payments if item[0] == user_id)

    async def rewards_since(self, referrer_id: UUID, since: datetime) -> int:
        return (await self.stats(referrer_id, since))[2]

    async def extend_premium(self, user_id: UUID, days: int, now: datetime) -> datetime:
        user = next(u for u in self._users() if u.id == user_id)
        expires = user.subscription_expires_at
        start = expires if expires is not None and expires > now else now
        user.subscription_tier = SubscriptionTier.NOMAD
        user.subscription_expires_at = start + timedelta(days=days)
        return user.subscription_expires_at

    async def mark_rewarded(self, friend_id: UUID, now: datetime) -> None:
        next(u for u in self._users() if u.id == friend_id).referral_rewarded_at = now

    async def notify(self, user_id: UUID, texts: dict[str, str]) -> None:
        self._store.notifications.append((user_id, texts))


class FakeRentRemindersRepository:
    """In-memory напоминания об оплате аренды (TASK-109)."""

    def __init__(self, store: Store) -> None:
        self._store = store

    async def list_for_user(self, user_id: UUID) -> list[Any]:
        return sorted(
            (r for r in self._store.rent_reminders if r.user_id == user_id), key=lambda r: r.day
        )

    async def count_for_user(self, user_id: UUID) -> int:
        return len(await self.list_for_user(user_id))

    async def add(self, user_id: UUID, day: int, amount: Decimal, currency: str) -> Any:
        from bina.infrastructure.db.models import RentReminder

        reminder = RentReminder(
            id=uuid4(), user_id=user_id, day=day, amount=amount, currency=currency, paid_for=None
        )
        self._store.rent_reminders.append(reminder)
        return reminder

    async def delete(self, user_id: UUID, reminder_id: UUID) -> bool:
        before = len(self._store.rent_reminders)
        self._store.rent_reminders = [
            r
            for r in self._store.rent_reminders
            if not (r.id == reminder_id and r.user_id == user_id)
        ]
        return len(self._store.rent_reminders) < before

    async def mark_paid(self, user_id: UUID, reminder_id: UUID, due: Any) -> bool:
        for reminder in self._store.rent_reminders:
            if reminder.id == reminder_id and reminder.user_id == user_id:
                reminder.paid_for = due
                return True
        return False
