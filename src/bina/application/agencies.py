"""Кабинет риелтора / агентства (TASK-100).

Риелтор регистрируется сам (название и телефон через Telegram) и сразу размещает
``AGENCY_FREE_LISTINGS`` объявлений бесплатно (обычный хозяин — 5). Больше —
пакет на месяц (``AGENCY_PLANS``). Объявление можно сделать «⭐ Premium»: раз в сутки
оно само поднимается наверх поиска (``BUMP_PRICE_STARS`` в месяц).

Пока владелец тестирует (``PREMIUM_FOR_ALL=1``), всё это бесплатно: лимит — самый
большой пакет, Premium-объявления включаются без оплаты.
"""

import hashlib
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from bina.application.rent_reminders import TBILISI
from bina.application.subscriptions import premium_for_all

DEFAULT_FREE_LISTINGS = 10
# id:объявлений:звёзд — «start:20:300,pro:30:450,business:40:600»
DEFAULT_PLANS = "start:20:300,pro:30:450,business:40:600"
PLAN_DAYS = 30
DEFAULT_BUMP_PRICE_STARS = 100
BUMP_DAYS = 30
# Поднимается не чаще раза в сутки (с запасом на расписание раз в час)
BUMP_EVERY = timedelta(hours=20)
# За один запуск у одного агентства поднимается не больше — не занимать весь первый экран
BUMPS_PER_AGENCY_PER_RUN = 3
MAX_NAME = 80
MAX_DESCRIPTION = 1000

AGENCY_PAYLOAD_PREFIX = "agency:"
BUMP_PAYLOAD_PREFIX = "bump:"
BUMP_PLAN = "bump"


@dataclass(frozen=True, slots=True)
class AgencyPlan:
    id: str
    listings: int
    price_stars: int
    days: int = PLAN_DAYS

    @property
    def payload(self) -> str:
        return f"{AGENCY_PAYLOAD_PREFIX}{self.id}"


def _int(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        return default
    return value if value > 0 else default


def free_listings(env: Mapping[str, str] | None = None) -> int:
    """Объявлений бесплатно: ``AGENCY_FREE_LISTINGS`` (10)."""
    return _int(os.environ if env is None else env, "AGENCY_FREE_LISTINGS", DEFAULT_FREE_LISTINGS)


def bump_price(env: Mapping[str, str] | None = None) -> int:
    """Premium-объявление на месяц, звёзд: ``BUMP_PRICE_STARS`` (100)."""
    source = os.environ if env is None else env
    return _int(source, "BUMP_PRICE_STARS", DEFAULT_BUMP_PRICE_STARS)


def load_agency_plans(env: Mapping[str, str] | None = None) -> dict[str, AgencyPlan]:
    """Пакеты из ``AGENCY_PLANS``; кривая строка — пакеты по умолчанию."""
    source = os.environ if env is None else env
    raw = source.get("AGENCY_PLANS", "").strip() or DEFAULT_PLANS
    plans: dict[str, AgencyPlan] = {}
    try:
        for item in raw.split(","):
            plan_id, listings, price = (part.strip() for part in item.split(":"))
            if not plan_id or int(listings) <= 0 or int(price) <= 0:
                raise ValueError(item)
            plans[plan_id] = AgencyPlan(plan_id, int(listings), int(price))
    except ValueError:
        return load_agency_plans({"AGENCY_PLANS": DEFAULT_PLANS})
    return dict(sorted(plans.items(), key=lambda pair: pair[1].listings))


def is_agency_payload(payload: str) -> bool:
    return payload.startswith(AGENCY_PAYLOAD_PREFIX)


def is_bump_payload(payload: str) -> bool:
    return payload.startswith(BUMP_PAYLOAD_PREFIX)


def plan_for_payload(plans: Mapping[str, AgencyPlan], payload: str) -> AgencyPlan | None:
    if not payload.startswith(AGENCY_PAYLOAD_PREFIX):
        return None
    return plans.get(payload.removeprefix(AGENCY_PAYLOAD_PREFIX))


def bump_payload(listing_id: UUID) -> str:
    return f"{BUMP_PAYLOAD_PREFIX}{listing_id}"


def listing_from_bump_payload(payload: str) -> UUID | None:
    if not payload.startswith(BUMP_PAYLOAD_PREFIX):
        return None
    try:
        return UUID(payload.removeprefix(BUMP_PAYLOAD_PREFIX))
    except ValueError:
        return None


def plan_active(plan: str | None, expires_at: datetime | None, now: datetime) -> bool:
    return bool(plan) and expires_at is not None and expires_at > now


def listing_limit(
    plans: Mapping[str, AgencyPlan], plan: str | None, expires_at: datetime | None, now: datetime
) -> int:
    """Сколько объявлений агентство может держать в поиске."""
    if premium_for_all() and plans:
        return max(item.listings for item in plans.values())
    if plan_active(plan, expires_at, now) and plan in plans:
        return plans[plan].listings  # type: ignore[index]
    return free_listings()


def extended(current: datetime | None, now: datetime, days: int) -> datetime:
    """Продление: от текущего срока, если он ещё идёт."""
    start = current if current is not None and current > now else now
    return start + timedelta(days=days)


def bump_hour(listing_id: UUID) -> int:
    """Час (по Тбилиси, 9-21), в который объявление поднимается: у всех разный."""
    digest = hashlib.sha1(listing_id.bytes, usedforsecurity=False).digest()
    return 9 + digest[0] % 13


def bump_due(
    listing_id: UUID, bump_until: datetime | None, bumped_at: datetime | None, now: datetime
) -> bool:
    """Пора поднять: Premium идёт, сегодня его час наступил, а поднимали давно."""
    if bump_until is None or bump_until <= now:
        return False
    if bumped_at is not None and now - bumped_at < BUMP_EVERY:
        return False
    return now.astimezone(TBILISI).hour >= bump_hour(listing_id)


def clean_name(text: str | None) -> str | None:
    name = " ".join((text or "").split())
    return name if 2 <= len(name) <= MAX_NAME else None
