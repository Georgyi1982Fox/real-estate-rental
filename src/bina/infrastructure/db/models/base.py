from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


class TimestampMixin:
    """Миксин для автоматических временных меток."""
    
    created_at: Column[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Column[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Миксин для мягкого удаления."""
    
    is_deleted: Column[bool] = Column(
        Boolean,
        default=False,
        nullable=False,
    )
    deleted_at: Column[datetime | None] = Column(
        DateTime(timezone=True),
        nullable=True,
    )


class Base(DeclarativeBase, TimestampMixin):
    """Базовый класс для всех моделей."""
    
    __abstract__ = True
    
    def to_dict(self) -> dict[str, Any]:
        """Преобразует объект в словарь."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }