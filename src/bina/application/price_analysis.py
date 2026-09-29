"""Анализ цены: дешевле или дороже обычного для района (TASK-093).

Сравнение с медианой похожих квартир: тот же район и столько же комнат (4 и больше
— одна группа). Если таких мало — медиана цены за м² района, умноженная на площадь.
Отличие до :data:`FAIR_BAND` в обе стороны — обычная цена.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

# ±10% от медианы — «обычная цена»
FAIR_BAND = Decimal("0.10")
# Меньше объявлений — медиана ненадёжна
MIN_SAMPLES = 5
# 4 комнаты и больше сравниваются между собой
ROOMS_GROUP_MAX = 4


class PriceLevel(StrEnum):
    """Оценка цены."""

    BELOW = "below"  # дешевле обычного
    FAIR = "fair"  # обычная цена
    ABOVE = "above"  # дороже обычного
    UNKNOWN = "unknown"  # мало данных для сравнения


class PriceBasis(StrEnum):
    """С чем сравнивали."""

    DISTRICT_ROOMS = "district_rooms"  # квартиры с тем же числом комнат в районе
    DISTRICT_M2 = "district_m2"  # цена за м² в районе, умноженная на площадь


@dataclass(frozen=True, slots=True)
class PriceAnalysis:
    """Итог сравнения цены."""

    level: PriceLevel
    # На сколько процентов цена отличается от обычной (минус — дешевле)
    diff_percent: int | None = None
    # Обычная цена такой квартиры (медиана), в валюте объявления
    typical_price: Decimal | None = None
    # Сколько объявлений в сравнении
    sample: int | None = None
    basis: PriceBasis | None = None


UNKNOWN = PriceAnalysis(level=PriceLevel.UNKNOWN)


def rooms_group(rooms: int) -> int:
    """Группа комнат для сравнения: 1, 2, 3, 4+ (как фильтр «4 и больше»)."""
    return min(rooms, ROOMS_GROUP_MAX)


def compare_price(
    price: Decimal, typical: Decimal, sample: int, basis: PriceBasis
) -> PriceAnalysis:
    """Оценка цены относительно обычной."""
    if typical <= 0 or price <= 0 or sample < MIN_SAMPLES:
        return UNKNOWN
    diff = (price - typical) / typical
    if diff < -FAIR_BAND:
        level = PriceLevel.BELOW
    elif diff > FAIR_BAND:
        level = PriceLevel.ABOVE
    else:
        level = PriceLevel.FAIR
    return PriceAnalysis(
        level=level,
        diff_percent=int((diff * 100).to_integral_value()),
        typical_price=typical.quantize(Decimal(1)),
        sample=sample,
        basis=basis,
    )
