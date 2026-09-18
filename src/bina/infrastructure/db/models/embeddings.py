from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


if TYPE_CHECKING:
    from .listings import Listing


class Embedding(Base):
    """Модель эмбеддингов для объявлений."""
    
    __tablename__ = "bina_embeddings"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    listing_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_listings.id"),
        nullable=False,
    )
    vector: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(
        String,
        default="text-embedding-3-small",
        nullable=False,
    )
    
    # Relationships
    listing: Mapped["Listing"] = relationship(
        back_populates="embeddings",
    )