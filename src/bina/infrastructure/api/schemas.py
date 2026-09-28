"""Схемы ответов API (контракт — ``frontend/src/api/types.ts``)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from bina.application.dtos.pagination import Page
from bina.application.fraud import fraud_level
from bina.application.subscriptions import Limits, Plan, effective_tier
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.db.models import District, Listing, Notification, SavedSearch, User
from bina.infrastructure.db.models.users import SubscriptionTier

# Текст на нескольких языках: {"ka": ..., "ru": ..., "en": ...}; пустые языки опускаются
Localized = dict[str, str]


def localized(**texts: str | None) -> Localized:
    """Словарь переводов без пустых значений."""
    return {language: text for language, text in texts.items() if text}


class ListingOut(BaseModel):
    """Объявление в формате фронтенда."""

    id: UUID
    title: Localized
    description: Localized
    price: float
    currency: str
    rooms: int
    area: float
    district: UUID = Field(description="ID района, название — в GET /api/districts")
    is_verified: bool
    images: list[str] = Field(default_factory=list)
    has_phone: bool = Field(
        default=False, description="Есть ли телефон (GET /api/listings/{id}/phone)"
    )
    source_url: str | None = Field(default=None, description="Объявление на сайте-источнике")
    owner_name: str | None = None
    # TASK-011: проверка на мошенничество
    fraud_level: Literal["none", "warning", "high"] = Field(
        default="none", description="warning — показать ⚠️; high — скрыто из поиска"
    )
    fraud_reasons: list[str] = Field(
        default_factory=list, description="Коды причин (переводит фронтенд)"
    )

    @classmethod
    def from_model(cls, listing: Listing) -> "ListingOut":
        """Преобразует ORM-модель."""
        return cls(
            id=listing.id,
            title=localized(ka=listing.title_ka, ru=listing.title_ru, en=listing.title_en),
            description=localized(
                ka=listing.description_ka, ru=listing.description_ru, en=listing.description_en
            ),
            price=float(listing.price),
            currency=listing.currency,
            rooms=listing.rooms,
            area=float(listing.area),
            district=listing.district_id,
            is_verified=listing.is_verified,
            images=list(listing.images or []),
            has_phone=bool(listing.phone),
            source_url=listing.url or None,
            owner_name=listing.owner_name or None,
            fraud_level=fraud_level(listing.fraud_score or 0).value,
            fraud_reasons=list(listing.fraud_reasons or []),
        )


class ListingsPageOut(BaseModel):
    """Страница объявлений; ``page`` нумеруется с 1."""

    items: list[ListingOut]
    total: int
    page: int
    pages: int

    @classmethod
    def from_page(cls, page: Page[Listing]) -> "ListingsPageOut":
        """Преобразует страницу use case (нумерация с 0) в ответ API (с 1)."""
        return cls(
            items=[ListingOut.from_model(listing) for listing in page.items],
            total=page.total,
            page=page.page + 1,
            pages=page.pages,
        )


class ListingsOut(BaseModel):
    """Список объявлений без пагинации."""

    items: list[ListingOut]


class DistrictOut(BaseModel):
    """Район."""

    id: UUID
    name: Localized

    @classmethod
    def from_model(cls, district: District) -> "DistrictOut":
        """Преобразует ORM-модель."""
        return cls(
            id=district.id,
            name=localized(ka=district.name_ka, ru=district.name_ru, en=district.name_en),
        )


class DistrictsOut(BaseModel):
    """Список районов."""

    items: list[DistrictOut]


class FavoriteIn(BaseModel):
    """Тело POST /api/favorites."""

    listing_id: UUID


class FavoriteIdsOut(BaseModel):
    """ID избранных объявлений."""

    ids: list[UUID]


class FavoriteOut(BaseModel):
    """Результат добавления в избранное."""

    listing_id: UUID
    is_favorite: bool = True


class PhoneOut(BaseModel):
    """Телефон арендодателя."""

    phone: str


class ContactOut(BaseModel):
    """Куда вести пользователя по кнопке «Написать»."""

    url: str


Language = Literal["ru", "en", "ka"]


class MeOut(BaseModel):
    """Профиль текущего пользователя.

    Имя и аватар бэкенд не хранит: фронтенд берёт их из ``Telegram.WebApp.initDataUnsafe.user``.
    """

    telegram_id: int
    language: str
    # С учётом срока: истёкшая подписка — "free"
    subscription_tier: str
    # Только у действующей подписки
    subscription_expires_at: datetime | None
    is_premium: bool
    balance: float
    favorites_count: int
    created_at: datetime

    @classmethod
    def from_model(cls, user: User, favorites_count: int) -> "MeOut":
        """Преобразует ORM-модель."""
        tier = effective_tier(user, datetime.now(UTC))
        premium = tier != SubscriptionTier.FREE
        return cls(
            telegram_id=user.telegram_id,
            language=user.language,
            subscription_tier=tier.value,
            subscription_expires_at=user.subscription_expires_at if premium else None,
            is_premium=premium,
            balance=float(user.balance),
            favorites_count=favorites_count,
            created_at=user.created_at,
        )


class MeIn(BaseModel):
    """Тело PATCH /api/me."""

    language: Language


# ------------------------------------------------------ TASK-026: подписка


class PlanOut(BaseModel):
    """Платный тариф."""

    id: str
    tier: str
    days: int
    price_stars: int


class LimitsOut(BaseModel):
    """Ограничения тарифа; ``favorites: null`` — без ограничения."""

    favorites: int | None
    searches: int


class UsageOut(BaseModel):
    """Сколько уже использовано."""

    favorites: int
    searches: int


class SubscriptionOut(BaseModel):
    """Ответ ``GET /api/subscription``."""

    tier: str
    is_premium: bool
    expires_at: datetime | None
    limits: LimitsOut
    usage: UsageOut
    plans: list[PlanOut]

    @classmethod
    def build(
        cls,
        user: User,
        *,
        premium: bool,
        limits: Limits,
        favorites: int,
        searches: int,
        plans: list[Plan],
    ) -> "SubscriptionOut":
        """Собирает ответ."""
        return cls(
            tier=user.subscription_tier.value if premium else SubscriptionTier.FREE.value,
            is_premium=premium,
            expires_at=user.subscription_expires_at if premium else None,
            limits=LimitsOut(favorites=limits.favorites, searches=limits.searches),
            usage=UsageOut(favorites=favorites, searches=searches),
            plans=[
                PlanOut(id=p.id, tier=p.tier.value, days=p.days, price_stars=p.price_stars)
                for p in plans
            ],
        )


class InvoiceIn(BaseModel):
    """Тело ``POST /api/subscription/invoice``."""

    plan: str = Field(min_length=1, max_length=64)


class InvoiceOut(BaseModel):
    """Ссылка для ``Telegram.WebApp.openInvoice``."""

    url: str


# ------------------------------------------------------------- TASK-028: поиски


class SearchFiltersIn(BaseModel):
    """Фильтры сохранённого поиска (как параметры ``GET /api/listings``)."""

    district: UUID | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    rooms: int | None = Field(default=None, ge=1, le=10, description="4 = «4 и больше»")

    @model_validator(mode="after")
    def _check_prices(self) -> "SearchFiltersIn":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must be <= max_price")
        return self


class SearchFiltersOut(BaseModel):
    """Фильтры сохранённого поиска; незаданные поля не возвращаются."""

    district: UUID | None = None
    min_price: float | None = None
    max_price: float | None = None
    rooms: int | None = None


class SearchIn(BaseModel):
    """Тело ``POST /api/searches``."""

    name: str | None = Field(default=None, max_length=100)
    filters: SearchFiltersIn = Field(default_factory=SearchFiltersIn)
    notify: bool = True

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str | None) -> str | None:
        # Пустое после очистки — название соберётся из фильтров
        return (clean_text(value) or None) if value is not None else None


class SearchPatchIn(BaseModel):
    """Тело ``PATCH /api/searches/{id}``."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    notify: bool | None = None

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_text(value)
        if not cleaned:
            raise ValueError("name must contain visible text")
        return cleaned


class SavedSearchOut(BaseModel):
    """Сохранённый поиск."""

    id: UUID
    name: str
    filters: SearchFiltersOut
    notify: bool
    new_count: int = Field(description="Новых квартир с последнего просмотра поиска")
    created_at: datetime

    @classmethod
    def from_model(cls, search: SavedSearch, new_count: int) -> "SavedSearchOut":
        """Преобразует ORM-модель."""
        return cls(
            id=search.id,
            name=search.name,
            filters=SearchFiltersOut(
                district=search.district_id,
                min_price=float(search.price_min) if search.price_min is not None else None,
                max_price=float(search.price_max) if search.price_max is not None else None,
                rooms=search.rooms,
            ),
            notify=search.notify,
            new_count=new_count,
            created_at=search.created_at,
        )


class SavedSearchesOut(BaseModel):
    """Список сохранённых поисков."""

    items: list[SavedSearchOut]


# ------------------------------------------------------- TASK-028: уведомления


class NotificationListingOut(BaseModel):
    """Квартира в уведомлении."""

    id: UUID
    title: Localized
    price: float
    currency: str
    image: str | None = None


class NotificationOut(BaseModel):
    """Уведомление."""

    id: UUID
    type: str
    created_at: datetime
    is_read: bool
    listing: NotificationListingOut | None = None
    old_price: float | None = None
    search_id: UUID | None = None
    search_name: str | None = None
    text: Localized | None = None

    @classmethod
    def from_model(cls, notification: Notification) -> "NotificationOut":
        """Преобразует ORM-модель (``listing`` и ``search`` должны быть загружены)."""
        listing = notification.listing
        return cls(
            id=notification.id,
            type=notification.type,
            created_at=notification.created_at,
            is_read=notification.is_read,
            listing=NotificationListingOut(
                id=listing.id,
                title=localized(ka=listing.title_ka, ru=listing.title_ru, en=listing.title_en),
                price=float(listing.price),
                currency=listing.currency,
                image=listing.images[0] if listing.images else None,
            )
            if listing is not None
            else None,
            old_price=float(notification.old_price) if notification.old_price is not None else None,
            search_id=notification.search_id,
            search_name=notification.search.name if notification.search else None,
            text={str(k): str(v) for k, v in notification.text.items() if v}
            if notification.text
            else None,
        )


class NotificationsPageOut(BaseModel):
    """Страница уведомлений; ``page`` нумеруется с 1."""

    items: list[NotificationOut]
    total: int
    page: int
    pages: int
    unread_count: int


class UnreadCountOut(BaseModel):
    """Число непрочитанных уведомлений."""

    count: int
