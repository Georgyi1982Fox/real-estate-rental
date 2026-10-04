"""«Вам может понравиться» (TASK-076): квартиры, похожие на избранное.

Без AI и бесплатно. По избранному собирается «вкус»: город, вид аренды, районы, комнаты и
обычная цена. Кандидаты — свежие объявления того же города и вида аренды; каждый получает
баллы за свой район, похожее число комнат и близкую цену. Избранное в подборку не попадает.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from uuid import UUID

from bina.application.costs import GEL_RATES
from bina.infrastructure.db.models import Listing

RECOMMENDATIONS_LIMIT = 10
# Сколько свежих объявлений рассматривать (дальше — сортировка по баллам)
CANDIDATES = 300
# Избранное, по которому считается вкус (последние)
TASTE_FROM = 30


@dataclass(frozen=True, slots=True)
class Taste:
    city: str | None
    rent_period: str
    district_ids: frozenset[UUID]
    rooms: frozenset[int]
    price_gel: Decimal | None


def price_gel(listing: Listing) -> Decimal | None:
    rate = GEL_RATES.get((listing.currency or "").upper())
    return Decimal(listing.price) * rate if rate is not None and listing.price else None


def taste_of(favorites: Sequence[Listing], cities: dict[UUID, str]) -> Taste | None:
    """Вкус по избранному; ``None`` — избранного нет."""
    if not favorites:
        return None
    period = Counter(item.rent_period for item in favorites).most_common(1)[0][0]
    same = [item for item in favorites if item.rent_period == period]
    city_counts = Counter(cities[item.district_id] for item in same if item.district_id in cities)
    prices = [value for item in same if (value := price_gel(item)) is not None]
    return Taste(
        city=city_counts.most_common(1)[0][0] if city_counts else None,
        rent_period=period,
        district_ids=frozenset(item.district_id for item in same),
        rooms=frozenset(item.rooms for item in same),
        price_gel=Decimal(median(prices)) if prices else None,
    )


def score(listing: Listing, taste: Taste) -> float:
    """Насколько квартира похожа на избранное (больше — лучше)."""
    points = 0.0
    if listing.district_id in taste.district_ids:
        points += 3
    if listing.rooms in taste.rooms:
        points += 2
    elif any(abs(listing.rooms - rooms) == 1 for rooms in taste.rooms):
        points += 1
    value = price_gel(listing)
    if taste.price_gel and value is not None:
        difference = abs(value - taste.price_gel) / taste.price_gel
        points += max(0.0, 2 * (1 - float(difference) * 2))  # ±50% и дальше — 0
    return points


def pick(
    candidates: Sequence[Listing], taste: Taste, exclude: set[UUID], limit: int
) -> list[Listing]:
    """Лучшие по баллам; при равных — свежие (кандидаты уже отсортированы по свежести)."""
    ranked = sorted(
        (item for item in candidates if item.id not in exclude),
        key=lambda item: -score(item, taste),
    )
    return [item for item in ranked if score(item, taste) > 0][:limit]
