import enum
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin

if TYPE_CHECKING:
    from .listings import Listing


class UserRole(str, enum.Enum):
    """Роли пользователей."""
    
    USER = "user"
    REALTOR = "realtor"
    ADMIN = "admin"


class SubscriptionTier(str, enum.Enum):
    """Уровни подписки."""
    
    FREE = "free"
    NOMAD = "nomad"
    FAMILY = "family"
    REALTOR = "realtor"


class User(Base, SoftDeleteMixin):
    """Модель пользователя."""
    
    __tablename__ = "bina_users"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(
        String(3),
        default="ru",
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        default=UserRole.USER,
        nullable=False,
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        default=SubscriptionTier.FREE,
        nullable=False,
    )
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    
    # Relationships
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )