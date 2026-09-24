import enum
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    # TASK-007: добавлены недостающие импорты для аннотаций relationship (mypy name-defined).
    from .users import User


class PaymentProvider(str, enum.Enum):
    """Провайдеры платежей."""
    
    TELEGRAM_STARS = "telegram_stars"
    STRIPE = "stripe"


class PaymentStatus(str, enum.Enum):
    """Статусы платежей."""
    
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Payment(Base):
    """Модель платежей."""
    
    __tablename__ = "bina_payments"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_users.id"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    provider: Mapped[PaymentProvider] = mapped_column(
        nullable=False,
    )
    provider_payment_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        nullable=False,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="payments",
    )