from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


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
    
    # Уникальный индекс (user_id, listing_id) - обеспечивается primary_key=True для обоих полей
    
    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_favorites_user_listing"),
    )