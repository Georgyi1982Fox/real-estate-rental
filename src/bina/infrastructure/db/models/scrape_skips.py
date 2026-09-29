"""Объявления источника, которые не стали объявлениями в базе (TASK-091).

Например, пост Telegram-канала о продаже или «ищу квартиру»: AI его уже разобрал,
повторно тратить запрос незачем.
"""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class ScrapeSkip(Base):
    """Пропущенное объявление источника (не аренда, не тот город, не хватает данных)."""

    __tablename__ = "bina_scrape_skips"

    source_name: Mapped[str] = mapped_column(String(20), primary_key=True)
    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    skipped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
