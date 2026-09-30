"""Сравнение квартир (TASK-105): до 3 объявлений в одной таблице.

Для каждой квартиры считаются цена в лари, цена за м², сколько отдать при въезде
и в среднем в месяц (калькулятор TASK-103), время до центра (TASK-104), оценка цены
(TASK-093) и риска (TASK-094). Лучшее значение в каждой строке отмечается.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

Labels = dict[str, str]

MIN_ITEMS = 2
MAX_ITEMS = 3

# Строки таблицы в порядке показа и подписи на трёх языках
ROWS: dict[str, Labels] = {
    "price": {"ka": "ქირა თვეში", "ru": "Аренда в месяц", "en": "Rent per month"},
    "price_per_m2": {"ka": "ფასი 1 მ²-ზე", "ru": "Цена за м²", "en": "Price per m²"},
    "area": {"ka": "ფართი", "ru": "Площадь", "en": "Area"},
    "rooms": {"ka": "ოთახები", "ru": "Комнаты", "en": "Rooms"},
    "floor": {"ka": "სართული", "ru": "Этаж", "en": "Floor"},
    "district": {"ka": "უბანი", "ru": "Район", "en": "District"},
    "minutes_to_center": {
        "ka": "ცენტრამდე (მანქანით)",
        "ru": "До центра (на машине)",
        "en": "To the centre (by car)",
    },
    "metro": {"ka": "მეტრო", "ru": "Метро", "en": "Metro"},
    "move_in": {"ka": "შესვლისას გადასახდელი", "ru": "Отдать при въезде", "en": "Pay at move-in"},
    "average_month": {
        "ka": "საშუალოდ თვეში კომუნალურით",
        "ru": "В среднем в месяц с коммунальными",
        "en": "Average month with utilities",
    },
    "price_level": {"ka": "ფასის შეფასება", "ru": "Оценка цены", "en": "Price check"},
    "risk_level": {"ka": "რისკი", "ru": "Риск", "en": "Risk"},
    "features": {"ka": "კეთილმოწყობა", "ru": "Удобства", "en": "Amenities"},
}

# Что сравнивается и в какую сторону лучше
_LOWER_IS_BETTER = ("price", "price_per_m2", "minutes_to_center", "move_in", "average_month")
_HIGHER_IS_BETTER = ("area", "features")
_RISK_ORDER = {"none": 0, "warning": 1, "high": 2}


@dataclass(frozen=True, slots=True)
class ComparedValues:
    """Числа одной квартиры для выбора лучшего (``None`` — неизвестно)."""

    listing_id: UUID
    price: Decimal
    price_per_m2: Decimal | None
    area: float
    minutes_to_center: int | None
    move_in: Decimal
    average_month: Decimal
    features: int
    risk_level: str


def best_in_rows(items: list[ComparedValues]) -> dict[str, list[UUID]]:
    """Для каждой строки — квартиры с лучшим значением.

    Строка без отметки, если значение известно меньше чем у двух квартир или у всех одинаковое.
    """
    best: dict[str, list[UUID]] = {}
    rows: list[tuple[str, bool]] = [(row, False) for row in _LOWER_IS_BETTER]
    rows += [(row, True) for row in _HIGHER_IS_BETTER]
    for row, higher in rows:
        values = [
            (item.listing_id, value) for item in items if (value := getattr(item, row)) is not None
        ]
        _mark(best, row, values, higher)
    risks = [(item.listing_id, _RISK_ORDER.get(item.risk_level, 0)) for item in items]
    _mark(best, "risk_level", risks, higher=False)
    return best


def _mark(
    best: dict[str, list[UUID]],
    row: str,
    values: Sequence[tuple[UUID, Decimal | float | int]],
    higher: bool,
) -> None:
    if len(values) < MIN_ITEMS:
        return
    numbers = [value for _, value in values]
    target = max(numbers) if higher else min(numbers)
    if all(value == target for value in numbers):
        return
    best[row] = [listing_id for listing_id, value in values if value == target]
