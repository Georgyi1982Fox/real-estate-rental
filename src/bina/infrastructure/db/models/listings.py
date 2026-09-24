import enum
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin

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
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    fraud_score: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    status: Mapped[ListingStatus] = mapped_column(
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