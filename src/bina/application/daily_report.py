"""Ежедневный отчёт владельцу в Telegram (TASK-041): что произошло за сутки.

Отправляется один раз в день — в ``DAILY_REPORT_HOUR`` по Тбилиси (по умолчанию 9) или
при первом запуске расписания после этого часа. ``DAILY_REPORT=0`` — не присылать.
"""

import os
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from bina.application.rent_reminders import TBILISI

DEFAULT_REPORT_HOUR = 9


@dataclass(frozen=True, slots=True)
class DailyReport:
    """Цифры за последние 24 часа (и сколько всего сейчас)."""

    users: int
    users_new: int
    listings: int  # в поиске сейчас
    listings_new: int
    owner_listings_new: int  # от хозяев и риелторов через бота / Mini App
    agencies: int
    agencies_new: int
    chats_new: int
    viewings_new: int
    verifications_pending: int
    open_complaints: int
    payments: int
    stars: Decimal
    premium: int
    ai_requests: int


def daily_report_enabled() -> bool:
    return os.getenv("DAILY_REPORT", "1").strip() != "0"


def report_hour() -> int:
    raw = os.getenv("DAILY_REPORT_HOUR", "").strip()
    if raw.isdigit() and 0 <= int(raw) <= 23:
        return int(raw)
    return DEFAULT_REPORT_HOUR


def report_day(now: datetime) -> date | None:
    """За какой день пора отправить отчёт; ``None`` — ещё рано или отчёт выключен."""
    if not daily_report_enabled():
        return None
    local = now.astimezone(TBILISI)
    return local.date() if local.hour >= report_hour() else None
