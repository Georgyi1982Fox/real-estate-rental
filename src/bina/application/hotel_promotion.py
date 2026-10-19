"""«🔥 Топ» для гостиниц за звёзды Telegram (TASK-120, этап 2).

Как у квартир (TASK-097): хозяин платит, и объект ``PROMOTION_DAYS`` дней стоит первым
в разделе «Гостиницы» со значком «🔥 Топ». Повторная оплата продлевает срок.
Счёт открывает мини-приложение (``POST /api/my/hotels/{id}/promotion``), оплату
принимает бот (handlers/payments.py → handlers/hotels.py).
"""

import os
from uuid import UUID

DEFAULT_HOTEL_PROMOTION_PRICE_STARS = 150
# Счёт: ``htop:<id гостиницы без дефисов>`` (не путать с ``promo:`` у квартир)
HOTEL_PROMOTION_PAYLOAD_PREFIX = "htop:"
HOTEL_PROMOTION_PLAN = "hotel_promo"


def hotel_promotion_price() -> int:
    """Цена в звёздах: ``HOTEL_PROMOTION_PRICE_STARS`` в ``.env`` (по умолчанию 150)."""
    raw = os.getenv("HOTEL_PROMOTION_PRICE_STARS", "").strip()
    try:
        price = int(raw) if raw else DEFAULT_HOTEL_PROMOTION_PRICE_STARS
    except ValueError:
        return DEFAULT_HOTEL_PROMOTION_PRICE_STARS
    return price if price > 0 else DEFAULT_HOTEL_PROMOTION_PRICE_STARS


def hotel_promotion_payload(hotel_id: UUID) -> str:
    return f"{HOTEL_PROMOTION_PAYLOAD_PREFIX}{hotel_id.hex}"


def is_hotel_promotion_payload(payload: str) -> bool:
    return payload.startswith(HOTEL_PROMOTION_PAYLOAD_PREFIX)


def hotel_from_payload(payload: str) -> UUID | None:
    """ID гостиницы из счёта; ``None`` — это не счёт за «Топ» гостиницы."""
    if not is_hotel_promotion_payload(payload):
        return None
    try:
        return UUID(hex=payload.removeprefix(HOTEL_PROMOTION_PAYLOAD_PREFIX))
    except ValueError:
        return None
