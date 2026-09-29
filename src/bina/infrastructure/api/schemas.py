"""Схемы ответов API (контракт — ``frontend/src/api/types.ts``)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from bina.application.dtos.pagination import Page
from bina.application.fraud import fraud_level
from bina.application.listing_details import CONDITIONS, FEATURES, clean_features
from bina.application.localization import localize_address, localize_name
from bina.application.price_analysis import PriceAnalysis, PriceLevel
from bina.application.risk_report import RiskReport
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
    also_on: list["SourceLinkOut"] = Field(
        default_factory=list,
        description="TASK-090: та же квартира на других сайтах (только в GET /api/listings/{id})",
    )
    owner_name: str | None = None
    # TASK-011: проверка на мошенничество
    fraud_level: Literal["none", "warning", "high"] = Field(
        default="none", description="warning — показать ⚠️; high — скрыто из поиска"
    )
    fraud_reasons: list[str] = Field(
        default_factory=list, description="Коды причин (переводит фронтенд)"
    )
    # TASK-018: подробности со страницы объявления (null — сайт не указал)
    floor: int | None = None
    total_floors: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    condition: str | None = Field(default=None, description="Код состояния (переводит фронтенд)")
    features: list[str] = Field(
        default_factory=list, description="Коды удобств (переводит фронтенд)"
    )
    owner_type: Literal["owner", "agent"] | None = None
    address: Localized = Field(
        default_factory=dict, description="Улица и дом на ka/ru/en (язык сайта — как на сайте)"
    )
    owner: "OwnerOut | None" = Field(default=None, description="Владелец: имя на ka/ru/en")
    latitude: float | None = None
    longitude: float | None = None
    published_at: datetime | None = Field(default=None, description="Опубликовано на сайте")
    updated_at: datetime | None = Field(default=None, description="Обновлено на сайте")

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
            floor=listing.floor,
            total_floors=listing.total_floors,
            bedrooms=listing.bedrooms,
            bathrooms=listing.bathrooms,
            condition=listing.condition,
            features=list(listing.features or []),
            owner_type=_owner_type(listing.owner_type),
            address=localize_address(listing.address),
            owner=OwnerOut.from_name(listing.owner_name),
            latitude=listing.latitude,
            longitude=listing.longitude,
            published_at=listing.source_published_at or listing.created_at,
            updated_at=listing.source_updated_at,
        )


class OwnerOut(BaseModel):
    """Владелец объявления; имя транслитерировано на три языка (TASK-019)."""

    name: Localized

    @classmethod
    def from_name(cls, name: str | None) -> "OwnerOut | None":
        """``None``, если сайт не указал имя."""
        names = localize_name(name)
        return cls(name=names) if names else None


class PriceAnalysisOut(BaseModel):
    """TASK-093: цена по сравнению с похожими квартирами района.

    ``level`` — всем; подробности (проценты, обычная цена, выборка) — только Premium,
    без него они ``null`` и ``premium_required: true``.
    """

    level: Literal["below", "fair", "above", "unknown"] = Field(
        description="below — дешевле обычного, fair — обычная цена, above — дороже, "
        "unknown — мало данных"
    )
    diff_percent: int | None = Field(
        default=None, description="На сколько % отличается от обычной (минус — дешевле)"
    )
    typical_price: float | None = Field(
        default=None, description="Обычная цена такой квартиры в районе (медиана)"
    )
    currency: str
    sample: int | None = Field(default=None, description="Сколько объявлений в сравнении")
    basis: Literal["district_rooms", "district_m2"] | None = Field(
        default=None,
        description="district_rooms — те же комнаты в районе, district_m2 — цена за м² района",
    )
    premium_required: bool = False

    @classmethod
    def build(cls, analysis: PriceAnalysis, currency: str, *, premium: bool) -> "PriceAnalysisOut":
        """Ответ с учётом тарифа."""
        known = analysis.level is not PriceLevel.UNKNOWN
        if not premium:
            return cls(level=analysis.level.value, currency=currency, premium_required=known)
        return cls(
            level=analysis.level.value,
            diff_percent=analysis.diff_percent,
            typical_price=float(analysis.typical_price) if analysis.typical_price else None,
            currency=currency,
            sample=analysis.sample,
            basis=analysis.basis.value if analysis.basis else None,
        )


class RiskReasonOut(BaseModel):
    """Причина подозрения: код — всем, название и объяснение — Premium."""

    code: str
    title: str | None = None
    explanation: str | None = None


class RiskOut(BaseModel):
    """TASK-094: разбор риска объявления.

    Всем: ``level`` и коды причин. Premium: названия и объяснения причин на языке
    пользователя и ``checklist`` — что проверить и спросить до встречи.
    """

    level: Literal["none", "warning", "high"]
    reasons: list[RiskReasonOut]
    checklist: list[str] = Field(default_factory=list)
    premium_required: bool = False

    @classmethod
    def build(cls, report: RiskReport, *, premium: bool) -> "RiskOut":
        """Ответ с учётом тарифа."""
        if not premium:
            return cls(
                level=report.level.value,
                reasons=[RiskReasonOut(code=code) for code, _ in report.reasons],
                premium_required=True,
            )
        return cls(
            level=report.level.value,
            reasons=[
                RiskReasonOut(code=code, title=text.title, explanation=text.explanation)
                for code, text in report.reasons
            ],
            checklist=report.checklist,
        )


class SourceLinkOut(BaseModel):
    """Та же квартира на другом сайте."""

    source: str = Field(description="myhome или ss")
    url: str


def _owner_type(value: str | None) -> Literal["owner", "agent"] | None:
    if value == "owner":
        return "owner"
    if value == "agent":
        return "agent"
    return None


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
    districts: list[UUID] = Field(
        default_factory=list, max_length=20, description="Несколько районов (любой из них)"
    )
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    rooms: int | None = Field(default=None, ge=1, le=10, description="4 = «4 и больше»")
    # TASK-086: остальные фильтры, как в GET /api/listings
    min_area: Decimal | None = Field(default=None, ge=0)
    max_area: Decimal | None = Field(default=None, ge=0)
    q: str | None = Field(default=None, max_length=200, description="Текст поиска")
    floor_min: int | None = Field(default=None, ge=0, le=100)
    floor_max: int | None = Field(default=None, ge=0, le=100)
    not_first_floor: bool = False
    not_last_floor: bool = False
    bedrooms: int | None = Field(default=None, ge=1, le=10, description="Спален от")
    bathrooms: int | None = Field(default=None, ge=1, le=10, description="Санузлов от")
    features: list[str] = Field(default_factory=list, description="Нужны все удобства")
    condition: list[str] = Field(default_factory=list, description="Любое из состояний")
    owner_only: bool = False

    @property
    def district_ids(self) -> list[UUID]:
        """``districts`` и ``district`` вместе, без повторов."""
        return list(dict.fromkeys([*self.districts, *([self.district] if self.district else [])]))

    @field_validator("q")
    @classmethod
    def _clean_query(cls, value: str | None) -> str | None:
        return (clean_text(value) or None) if value is not None else None

    @field_validator("features")
    @classmethod
    def _check_features(cls, value: list[str]) -> list[str]:
        unknown = sorted(set(value) - set(FEATURES))
        if unknown:
            raise ValueError(f"unknown features: {', '.join(unknown)}")
        return clean_features(value)

    @field_validator("condition")
    @classmethod
    def _check_condition(cls, value: list[str]) -> list[str]:
        unknown = sorted(set(value) - set(CONDITIONS))
        if unknown:
            raise ValueError(f"unknown condition: {', '.join(unknown)}")
        return [code for code in CONDITIONS if code in value]

    @model_validator(mode="after")
    def _check_prices(self) -> "SearchFiltersIn":
        for low, high, name in (
            (self.min_price, self.max_price, "min_price must be <= max_price"),
            (self.min_area, self.max_area, "min_area must be <= max_area"),
            (self.floor_min, self.floor_max, "floor_min must be <= floor_max"),
        ):
            if low is not None and high is not None and low > high:
                raise ValueError(name)
        return self

    def details(self) -> dict[str, Any]:
        """Фильтры для ``SavedSearch.details`` (только заданные; ключи ListingSearchFilters)."""
        values: dict[str, Any] = {
            "area_min": float(self.min_area) if self.min_area is not None else None,
            "area_max": float(self.max_area) if self.max_area is not None else None,
            "query": self.q,
            "floor_min": self.floor_min,
            "floor_max": self.floor_max,
            "not_first_floor": self.not_first_floor or None,
            "not_last_floor": self.not_last_floor or None,
            "bedrooms_min": self.bedrooms,
            "bathrooms_min": self.bathrooms,
            "features": self.features or None,
            "conditions": self.condition or None,
            "owner_only": self.owner_only or None,
        }
        return {key: value for key, value in values.items() if value is not None}


class SearchFiltersOut(BaseModel):
    """Фильтры сохранённого поиска; незаданные поля не возвращаются."""

    # Ровно один район; при нескольких — None, а все районы в ``districts``
    district: UUID | None = None
    districts: list[UUID] = Field(default_factory=list)
    min_price: float | None = None
    max_price: float | None = None
    rooms: int | None = None
    # TASK-086
    min_area: float | None = None
    max_area: float | None = None
    q: str | None = None
    floor_min: int | None = None
    floor_max: int | None = None
    not_first_floor: bool = False
    not_last_floor: bool = False
    bedrooms: int | None = None
    bathrooms: int | None = None
    features: list[str] = Field(default_factory=list)
    condition: list[str] = Field(default_factory=list)
    owner_only: bool = False

    @classmethod
    def from_model(cls, search: SavedSearch) -> "SearchFiltersOut":
        """Фильтры поиска: колонки и ``details``."""
        districts = search.all_district_ids
        details = search.details or {}
        return cls(
            district=districts[0] if len(districts) == 1 else None,
            districts=districts,
            min_price=float(search.price_min) if search.price_min is not None else None,
            max_price=float(search.price_max) if search.price_max is not None else None,
            rooms=search.rooms,
            min_area=details.get("area_min"),
            max_area=details.get("area_max"),
            q=details.get("query"),
            floor_min=details.get("floor_min"),
            floor_max=details.get("floor_max"),
            not_first_floor=bool(details.get("not_first_floor")),
            not_last_floor=bool(details.get("not_last_floor")),
            bedrooms=details.get("bedrooms_min"),
            bathrooms=details.get("bathrooms_min"),
            features=list(details.get("features") or []),
            condition=list(details.get("conditions") or []),
            owner_only=bool(details.get("owner_only")),
        )


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
            filters=SearchFiltersOut.from_model(search),
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
