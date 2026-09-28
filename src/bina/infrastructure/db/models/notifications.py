"""Сохранённые поиски и уведомления (TASK-028)."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .listings import Listing


class NotificationType(enum.StrEnum):
    """Типы уведомлений (строки в колонке ``type``)."""

    NEW_LISTING = "new_listing"
    PRICE_DROP = "price_drop"
    SYSTEM = "system"


class SavedSearch(Base):
    """Сохранённый поиск: фильтры и подписка на новые квартиры по ним."""

    __tablename__ = "bina_saved_searches"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    district_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_districts.id"), nullable=True
    )
    price_min: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    price_max: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    # 4 = «4 и больше», как в фильтре API
    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notify: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Уведомлять о квартирах, появившихся после этого момента (сдвигается при включении)
    notify_since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Счётчик «+N новых» считается от последнего просмотра поиска
    last_viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Notification(Base):
    """Уведомление пользователя: в Mini App (список) и в Telegram (``sent_at``)."""

    __tablename__ = "bina_notifications"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    listing_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_listings.id", ondelete="CASCADE"), nullable=True
    )
    search_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_saved_searches.id", ondelete="SET NULL"),
        nullable=True,
    )
    old_price: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    new_price: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    # Текст служебного уведомления: {"ru": ..., "en": ..., "ka": ...}
    text: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    listing: Mapped["Listing | None"] = relationship(lazy="raise")
    search: Mapped["SavedSearch | None"] = relationship(lazy="raise")
