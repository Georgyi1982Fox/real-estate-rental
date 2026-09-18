from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .listings import Listing
    from .users import User


class Favorite(Base):
    """Модель избранных объявлений."""

    __tablename__ = "bina_favorites"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_users.id"),
        primary_key=True,
    )
    listing_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_listings.id"),
        primary_key=True,
    )

    # Relationships
    listing: Mapped["Listing"] = relationship(
        back_populates="favorites",
    )
    user: Mapped["User"] = relationship(
        back_populates="favorites",
    )

    # Уникальный индекс (user_id, listing_id) - обеспечивается primary_key=True для обоих полей

    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_favorites_user_listing"),
    )