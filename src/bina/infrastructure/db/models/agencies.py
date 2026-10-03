"""Агентства и риелторы (TASK-100); статистика объявлений."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Agency(Base):
    """Кабинет риелтора: один на пользователя."""

    __tablename__ = "bina_agencies"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Оплаченный пакет (bina.application.agencies.AgencyPlan.id) и до какого времени
    plan: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Заблокирован владельцем сервиса: объявления скрыты, новые нельзя
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ListingStat(Base):
    """Сколько раз за день открыли объявление и нажали «Написать» / «Телефон»."""

    __tablename__ = "bina_listing_stats"

    listing_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_listings.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contacts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
