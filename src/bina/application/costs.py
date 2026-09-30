"""Калькулятор полной стоимости аренды (TASK-103).

Аренда + залог + комиссия + примерные коммунальные платежи по месяцам.
Коммунальные считаются по площади, числу жильцов и сезону (зимой — отопление).
Тарифы — примерные для Тбилиси, в лари; это оценка, а не счёт: разброс ±25%.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

# Курс к лари для аренды в долларах и евро (приблизительный, как в нормализаторе)
GEL_RATES: dict[str, Decimal] = {"GEL": Decimal(1), "USD": Decimal("2.7"), "EUR": Decimal("3.0")}

# Насколько реальные счета могут отличаться от оценки, %
RANGE_PERCENT = 25


@dataclass(frozen=True, slots=True)
class Tariffs:
    """Примерные тарифы, лари в месяц."""

    electricity_base: Decimal = Decimal(35)  # свет: техника, освещение
    electricity_per_m2: Decimal = Decimal("0.3")
    gas_base: Decimal = Decimal(12)  # газ: плита, горячая вода
    # Отопление за м² в месяц: зима (декабрь-февраль) и межсезонье (ноябрь, март)
    gas_heating_winter_per_m2: Decimal = Decimal("2.2")
    gas_heating_shoulder_per_m2: Decimal = Decimal("1.0")
    # Электрическое отопление дороже газового
    electric_heating_winter_per_m2: Decimal = Decimal("2.8")
    electric_heating_shoulder_per_m2: Decimal = Decimal("1.3")
    air_conditioning_per_m2: Decimal = Decimal("0.5")  # июль-август
    water_per_person: Decimal = Decimal(5)
    cleaning_per_person: Decimal = Decimal(4)  # уборка (приходит в счёте за свет)
    internet: Decimal = Decimal(45)
    building: Decimal = Decimal(15)  # ამხანაგობა: подъезд, лифт


TARIFFS = Tariffs()

WINTER_MONTHS = (12, 1, 2)
SHOULDER_MONTHS = (11, 3)
HOT_MONTHS = (7, 8)


class Heating(StrEnum):
    GAS = "gas"
    ELECTRIC = "electric"


class CostItem(StrEnum):
    ELECTRICITY = "electricity"
    GAS = "gas"
    WATER = "water"
    CLEANING = "cleaning"
    INTERNET = "internet"
    BUILDING = "building"


ITEM_LABELS: dict[CostItem, dict[str, str]] = {
    CostItem.ELECTRICITY: {"ka": "ელექტროენერგია", "ru": "Электричество", "en": "Electricity"},
    CostItem.GAS: {"ka": "გაზი", "ru": "Газ", "en": "Gas"},
    CostItem.WATER: {"ka": "წყალი", "ru": "Вода", "en": "Water"},
    CostItem.CLEANING: {"ka": "დასუფთავება", "ru": "Уборка и вывоз мусора", "en": "Cleaning fee"},
    CostItem.INTERNET: {"ka": "ინტერნეტი", "ru": "Интернет", "en": "Internet"},
    CostItem.BUILDING: {"ka": "ამხანაგობა", "ru": "Подъезд и лифт", "en": "Building fee"},
}

NOTE: dict[str, str] = {
    "ka": "მიახლოებითი გათვლა. რეალური გადასახადები დამოკიდებულია სეზონზე, მოხმარებასა და "
    "გათბობის ტიპზე; სხვაობა შეიძლება იყოს ±{range}%.",
    "ru": "Примерный расчёт. Реальные счета зависят от сезона, расхода и типа отопления; "
    "разница может быть ±{range}%.",
    "en": "Approximate estimate. Real bills depend on the season, usage and heating type; "
    "they may differ by ±{range}%.",
}


@dataclass(frozen=True, slots=True)
class CostInput:
    """Что известно о квартире и что выбрал пользователь."""

    rent: Decimal
    currency: str
    area: float
    features: tuple[str, ...]
    start: date
    months: int = 12
    people: int = 2
    deposit_months: Decimal = Decimal(1)
    agency_fee_percent: Decimal = Decimal(0)
    utilities_included: bool = False


@dataclass(frozen=True, slots=True)
class MonthCost:
    month: date  # первое число месяца
    items: dict[CostItem, Decimal]
    utilities: Decimal
    total: Decimal  # аренда + коммунальные


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Результат в лари."""

    rent: Decimal
    rent_currency: str
    exchange_rate: Decimal
    deposit: Decimal
    agency_fee: Decimal
    heating: Heating
    air_conditioning: bool
    months: list[MonthCost]
    first_month_total: Decimal  # аренда + залог + комиссия + коммунальные первого месяца
    average_utilities: Decimal
    average_month: Decimal  # аренда + средние коммунальные
    period_total: Decimal  # аренда и коммунальные за весь срок + комиссия (залог вернётся)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def heating_type(features: tuple[str, ...]) -> Heating:
    """Газовое отопление — обычное для Тбилиси; электрическое — если газа нет в удобствах.

    Если удобства не указаны вовсе, считаем газовое.
    """
    if not features or "gas" in features or "heating" in features:
        return Heating.GAS
    return Heating.ELECTRIC


def month_utilities(
    month: int,
    area: float,
    people: int,
    heating: Heating,
    air_conditioning: bool,
    tariffs: Tariffs = TARIFFS,
) -> dict[CostItem, Decimal]:
    """Коммунальные за один месяц по статьям."""
    m2 = Decimal(str(area))
    electricity = tariffs.electricity_base + tariffs.electricity_per_m2 * m2
    gas = tariffs.gas_base
    if month in WINTER_MONTHS or month in SHOULDER_MONTHS:
        winter = month in WINTER_MONTHS
        if heating is Heating.GAS:
            rate = (
                tariffs.gas_heating_winter_per_m2 if winter else tariffs.gas_heating_shoulder_per_m2
            )
            gas += rate * m2
        else:
            rate = (
                tariffs.electric_heating_winter_per_m2
                if winter
                else tariffs.electric_heating_shoulder_per_m2
            )
            electricity += rate * m2
    if air_conditioning and month in HOT_MONTHS:
        electricity += tariffs.air_conditioning_per_m2 * m2
    return {
        CostItem.ELECTRICITY: _money(electricity),
        CostItem.GAS: _money(gas),
        CostItem.WATER: _money(tariffs.water_per_person * people),
        CostItem.CLEANING: _money(tariffs.cleaning_per_person * people),
        CostItem.INTERNET: tariffs.internet,
        CostItem.BUILDING: tariffs.building,
    }


def _add_months(start: date, offset: int) -> date:
    index = start.month - 1 + offset
    return date(start.year + index // 12, index % 12 + 1, 1)


def estimate_costs(data: CostInput, tariffs: Tariffs = TARIFFS) -> CostEstimate:
    """Полная стоимость на срок аренды, в лари."""
    rate = GEL_RATES.get(data.currency.upper())
    if rate is None:
        raise ValueError(f"unsupported currency: {data.currency}")
    rent = _money(data.rent * rate)
    heating = heating_type(data.features)
    air_conditioning = "air_conditioning" in data.features
    months = []
    for offset in range(data.months):
        month = _add_months(data.start, offset)
        items = (
            {}
            if data.utilities_included
            else month_utilities(
                month.month, data.area, data.people, heating, air_conditioning, tariffs
            )
        )
        utilities = sum(items.values(), Decimal(0))
        months.append(MonthCost(month, items, utilities, rent + utilities))
    deposit = _money(rent * data.deposit_months)
    agency_fee = _money(rent * data.agency_fee_percent / 100)
    utilities_total = sum((month.utilities for month in months), Decimal(0))
    average_utilities = _money(utilities_total / len(months))
    return CostEstimate(
        rent=rent,
        rent_currency=data.currency.upper(),
        exchange_rate=rate,
        deposit=deposit,
        agency_fee=agency_fee,
        heating=heating,
        air_conditioning=air_conditioning,
        months=months,
        first_month_total=rent + deposit + agency_fee + months[0].utilities,
        average_utilities=average_utilities,
        average_month=rent + average_utilities,
        period_total=rent * len(months) + utilities_total + agency_fee,
    )
