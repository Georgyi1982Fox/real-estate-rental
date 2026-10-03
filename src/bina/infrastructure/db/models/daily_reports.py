"""Какие ежедневные отчёты владельцу уже отправлены (TASK-041)."""

from datetime import date

from sqlalchemy import Date
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DailyReportRecord(Base):
    """Отчёт за день отправлен (``created_at``) — второй раз в тот же день не шлём."""

    __tablename__ = "bina_daily_reports"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
