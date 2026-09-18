from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class TimestampMixin:
    """Миксин для автоматических временных меток."""

    __allow_unmapped__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Миксин для мягкого удаления."""

    __allow_unmapped__ = True

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Base(DeclarativeBase, TimestampMixin):
    """Базовый класс для всех моделей."""

    __abstract__ = True
    __allow_unmapped__ = True

    def to_dict(self) -> dict[str, Any]:
        """Преобразует объект в словарь."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }