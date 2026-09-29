import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, value_enum

if TYPE_CHECKING:
    from .districts import District

    # TASK-007: Favorite импортировался из .users, где его нет; Embedding не импортировался.
    from .embeddings import Embedding
    from .favorites import Favorite


class ListingStatus(str, enum.Enum):
    """Статусы объявлений."""

    ACTIVE = "active"
    SOLD = "sold"
    ARCHIVED = "archived"


class Listing(Base, SoftDeleteMixin):
    """Модель объявления о недвижимости."""

    __tablename__ = "bina_listings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    source_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    title_ru: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    title_ka: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    description_ru: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description_ka: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    # TASK-028: цена до последнего изменения (уведомление «цена снижена»)
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    price_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # TASK-010: английский перевод; пустая строка — перевода ещё нет
    title_en: Mapped[str] = mapped_column(
        String,
        default="",
        server_default="",
        nullable=False,
    )
    description_en: Mapped[str] = mapped_column(
        Text,
        default="",
        server_default="",
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String,
        default="GEL",
        nullable=False,
    )
    district_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_districts.id"),
        nullable=False,
    )
    rooms: Mapped[int] = mapped_column(
        nullable=False,
    )
    area: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    # Ссылки на фото (URL или пути фронтенда); миграция listing_images
    images: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    # Источник и контакты (миграция listing_contacts)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    fraud_score: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    # TASK-018: подробности со страницы объявления (None — источник не дал)
    floor: Mapped[int | None] = mapped_column(nullable=True)
    total_floors: Mapped[int | None] = mapped_column(nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(nullable=True)
    # Коды из bina.application.listing_details
    condition: Mapped[str | None] = mapped_column(String, nullable=True)
    features: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    owner_type: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    source_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Когда загружена страница объявления; None — только данные из списка
    details_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # TASK-090: та же квартира на другом сайте (или повторно на том же) — ссылка на
    # основное объявление; пока основное в поиске, дубликат скрыт
    duplicate_of: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_listings.id", ondelete="SET NULL"), nullable=True
    )
    # Когда искали дубликаты; None — ещё не искали (или изменилась цена)
    duplicates_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Когда объявление последний раз видели на сайте (в списке или на его странице);
    # старые проверяются заново, снятые уходят в архив. None — ещё не проверяли
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # TASK-011: коды причин (bina.application.ports.fraud.REASONS) и время проверки;
    # None — ещё не проверено (или текст/цена изменились и нужна новая проверка)
    fraud_reasons: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    fraud_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # TASK-007: value_enum: хранить значения enum, как в миграции
    status: Mapped[ListingStatus] = mapped_column(
        value_enum(ListingStatus, "listingstatus"),
        default=ListingStatus.ACTIVE,
        nullable=False,
    )

    # Relationships
    district: Mapped["District"] = relationship(
        back_populates="listings",
    )
    embeddings: Mapped[list["Embedding"]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
    )
