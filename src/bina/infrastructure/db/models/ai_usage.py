"""Сколько запросов к AI-помощнику сделал пользователь за день (TASK-095)."""

from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AIUsage(Base):
    """Счётчик запросов пользователя к AI за день (дневной лимит — расход на AI)."""

    __tablename__ = "bina_ai_usage"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
