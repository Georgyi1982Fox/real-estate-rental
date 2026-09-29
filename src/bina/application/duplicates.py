"""Та же квартира на двух сайтах (TASK-090).

Одну квартиру часто выставляют и на SS.ge, и на MyHome.ge (или повторно на том же
сайте). Объявления считаются одной квартирой, если совпадают комнаты, этаж и
этажность (если известны), площадь и цена почти равны, и квартира в том же месте:
координаты ближе :data:`MAX_DISTANCE_M`, а без координат — тот же телефон.
"""

import math
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

# Допустимая разница площади и цены (сайты округляют, цену пересчитывают из $)
AREA_TOLERANCE = 0.03
PRICE_TOLERANCE = 0.05
# Одна точка на карте: сайты ставят метку на дом, иногда со сдвигом
MAX_DISTANCE_M = 100.0
# Последние цифры номера: +995 555 12 34 56 и 555123456 — один телефон
PHONE_DIGITS = 9


class ApartmentFacts(Protocol):
    """Поля объявления, по которым сравниваются квартиры (только чтение)."""

    @property
    def rooms(self) -> int: ...
    @property
    def area(self) -> float | Decimal: ...
    @property
    def price(self) -> Decimal: ...
    @property
    def currency(self) -> str: ...
    @property
    def floor(self) -> int | None: ...
    @property
    def total_floors(self) -> int | None: ...
    @property
    def bedrooms(self) -> int | None: ...
    @property
    def latitude(self) -> float | None: ...
    @property
    def longitude(self) -> float | None: ...
    @property
    def phone(self) -> str | None: ...


@dataclass(frozen=True, slots=True)
class Bounds:
    """Диапазоны площади и цены, в которых ищутся кандидаты в дубликаты."""

    area_min: Decimal
    area_max: Decimal
    price_min: Decimal
    price_max: Decimal


def candidate_bounds(listing: ApartmentFacts) -> Bounds:
    """Площадь и цена кандидатов для поиска в базе."""
    area = Decimal(str(listing.area))
    price = Decimal(str(listing.price))
    area_tol = Decimal(str(AREA_TOLERANCE))
    price_tol = Decimal(str(PRICE_TOLERANCE))
    return Bounds(
        area_min=area * (1 - area_tol),
        area_max=area * (1 + area_tol),
        price_min=price * (1 - price_tol),
        price_max=price * (1 + price_tol),
    )


def _close(a: float | Decimal, b: float | Decimal, tolerance: float) -> bool:
    x, y = float(a), float(b)
    if x <= 0 or y <= 0:
        return False
    return abs(x - y) / max(x, y) <= tolerance


def _differ(a: int | None, b: int | None) -> bool:
    """Оба известны и не равны."""
    return a is not None and b is not None and a != b


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между точками, метры (формула гаверсинусов)."""
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(h))


def phone_key(phone: str | None) -> str | None:
    """Последние цифры телефона (без кода страны и форматирования)."""
    digits = re.sub(r"\D", "", phone or "")
    return digits[-PHONE_DIGITS:] if len(digits) >= PHONE_DIGITS else None


def same_apartment(a: ApartmentFacts, b: ApartmentFacts) -> bool:
    """Одна ли это квартира."""
    if a.rooms != b.rooms or a.currency != b.currency:
        return False
    if not _close(a.area, b.area, AREA_TOLERANCE) or not _close(a.price, b.price, PRICE_TOLERANCE):
        return False
    if (
        _differ(a.floor, b.floor)
        or _differ(a.total_floors, b.total_floors)
        or _differ(a.bedrooms, b.bedrooms)
    ):
        return False
    if None not in (a.latitude, a.longitude, b.latitude, b.longitude):
        # Координаты решают: у риелтора один телефон на много разных квартир
        assert a.latitude is not None and a.longitude is not None
        assert b.latitude is not None and b.longitude is not None
        return distance_m(a.latitude, a.longitude, b.latitude, b.longitude) <= MAX_DISTANCE_M
    # Без координат — только тот же телефон и известный одинаковый этаж
    phone = phone_key(a.phone)
    return (
        phone is not None
        and phone == phone_key(b.phone)
        and a.floor is not None
        and a.floor == b.floor
    )
