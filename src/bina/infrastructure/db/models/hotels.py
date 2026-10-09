"""Гостиницы, их номера и жалобы на них (TASK-120)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Hotel(Base):
    """Гостиница, гостевой дом, хостел или апарт-отель, размещённый пользователем."""

    __tablename__ = "bina_hotels"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # bina.application.hotels.KINDS
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Код города (bina.application.cities)
    city: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amenities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    check_in: Mapped[str | None] = mapped_column(String(5), nullable=True)
    check_out: Mapped[str | None] = mapped_column(String(5), nullable=True)
    # Описание на языке хозяина и переводы (пустые — ещё не переведено)
    description_ka: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_ru: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    images: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Telegram хозяина (https://t.me/<username>), если есть
    contact_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Хозяин снял объект с показа
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Скрыт модерацией или жалобами (как у квартир)
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Проверка ИИ (этап 2): балл как у квартир и когда проверено
    fraud_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fraud_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Платный «🔥 Топ» (этап 2)
    promoted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Самая низкая цена ночи в лари — для поиска и сортировки «от … за ночь»
    min_price_gel: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_guests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rooms: Mapped[list["HotelRoom"]] = relationship(
        back_populates="hotel",
        cascade="all, delete-orphan",
        order_by="HotelRoom.created_at",
        lazy="selectin",
    )


class HotelRoom(Base):
    """Тип номера: сколько гостей, цена за ночь, сколько таких номеров."""

    __tablename__ = "bina_hotel_rooms"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    hotel_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_hotels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # bina.application.hotels.ROOM_KINDS
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    guests: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GEL")
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    hotel: Mapped[Hotel] = relationship(back_populates="rooms")


class HotelComplaint(Base):
    """Жалоба на гостиницу: одна от пользователя (повторная обновляет причину)."""

    __tablename__ = "bina_hotel_complaints"

    hotel_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_hotels.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_users.id", ondelete="CASCADE"), primary_key=True
    )
    # Код причины: bina.application.complaints.REASONS
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
