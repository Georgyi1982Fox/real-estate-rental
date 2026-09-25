from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin

if TYPE_CHECKING:
    from .listings import Listing


class District(Base, SoftDeleteMixin):
    """Модель района."""

    __tablename__ = "bina_districts"
    __allow_unmapped__ = True

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )
    name_ru: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    name_ka: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    name_en: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    center_coordinates: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    avg_price_per_m2: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    safety_score: Mapped[int] = mapped_column(
        nullable=False,
    )
    # TASK-007: dict -> dict[str, Any] (mypy strict type-arg).
    infrastructure_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Relationships
    listings: Mapped[list["Listing"]] = relationship(
        back_populates="district",
        cascade="all, delete-orphan",
    )