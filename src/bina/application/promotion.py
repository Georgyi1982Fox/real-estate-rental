"""Платное продвижение объявления хозяина и проверка собственника (TASK-097, TASK-098).

Продвижение: хозяин платит звёздами Telegram, и объявление ``PROMOTION_DAYS`` дней
стоит вверху поиска (новые сверху), со значком «🔥 Топ», и ещё раз уходит в
уведомления тем, чей сохранённый поиск под него подходит. Повторная оплата продлевает.

Проверка собственника: хозяин присылает боту выписку из Публичного реестра, владелец
сервиса подтверждает — объявление получает значок «✅ Проверенный собственник».
Бесплатно.
"""

import os
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

PROMOTION_DAYS = 7
DEFAULT_PROMOTION_PRICE_STARS = 150
# Счёт за продвижение: ``promo:<id объявления>`` (подписка Premium — ``plan:<тариф>``)
PROMOTION_PAYLOAD_PREFIX = "promo:"
PROMOTION_PLAN = "promo"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def promotion_price() -> int:
    """Цена в звёздах: ``PROMOTION_PRICE_STARS`` в ``.env`` (по умолчанию 150)."""
    raw = os.getenv("PROMOTION_PRICE_STARS", "").strip()
    try:
        price = int(raw) if raw else DEFAULT_PROMOTION_PRICE_STARS
    except ValueError:
        return DEFAULT_PROMOTION_PRICE_STARS
    return price if price > 0 else DEFAULT_PROMOTION_PRICE_STARS


def promotion_payload(listing_id: UUID) -> str:
    return f"{PROMOTION_PAYLOAD_PREFIX}{listing_id}"


def listing_from_payload(payload: str) -> UUID | None:
    """ID объявления из счёта за продвижение; ``None`` — это не продвижение."""
    if not payload.startswith(PROMOTION_PAYLOAD_PREFIX):
        return None
    try:
        return UUID(payload.removeprefix(PROMOTION_PAYLOAD_PREFIX))
    except ValueError:
        return None


def is_promotion_payload(payload: str) -> bool:
    return payload.startswith(PROMOTION_PAYLOAD_PREFIX)


def extended_promotion(current: datetime | None, now: datetime) -> datetime:
    """До какого времени продвижение после оплаты: продление от текущего срока."""
    start = current if current is not None and current > now else now
    return start + timedelta(days=PROMOTION_DAYS)


def is_promoted(promoted_until: datetime | None, now: datetime) -> bool:
    return promoted_until is not None and promoted_until > now
