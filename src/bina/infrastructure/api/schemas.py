"""Схемы ответов API (контракт — ``frontend/src/api/types.ts``)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from bina.application.dtos.pagination import Page
from bina.infrastructure.db.models import District, Listing, User

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
    subscription_tier: str
    subscription_expires_at: datetime | None
    balance: float
    favorites_count: int
    created_at: datetime

    @classmethod
    def from_model(cls, user: User, favorites_count: int) -> "MeOut":
        """Преобразует ORM-модель."""
        return cls(
            telegram_id=user.telegram_id,
            language=user.language,
            subscription_tier=user.subscription_tier.value,
            subscription_expires_at=user.subscription_expires_at,
            balance=float(user.balance),
            favorites_count=favorites_count,
            created_at=user.created_at,
        )


class MeIn(BaseModel):
    """Тело PATCH /api/me."""

    language: Language
