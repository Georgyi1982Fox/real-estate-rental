"""AI-разбор фото объявления (TASK-114)."""

from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PhotoReportRecord(Base):
    """Уровень ремонта, видимые проблемы и короткий вывод на трёх языках."""

    __tablename__ = "bina_photo_reports"

    listing_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_listings.id", ondelete="CASCADE"), primary_key=True
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    issues: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    summary_ru: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary_ka: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Отпечаток проанализированных фото: другие фото — разбор устарел
    photos_hash: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(60), nullable=False, default="")
