"""Жалобы пользователей на объявления (TASK-106)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Complaint(Base):
    """Жалоба: одна от пользователя на объявление (повторная обновляет причину)."""

    __tablename__ = "bina_complaints"

    listing_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_listings.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_users.id", ondelete="CASCADE"), primary_key=True
    )
    # Код причины: bina.application.complaints.REASONS
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Когда админ разобрал жалобу (TASK-110); None — ещё открыта
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
