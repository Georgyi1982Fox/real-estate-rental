"""Калькулятор полной стоимости (TASK-103)."""

from datetime import date
from decimal import Decimal

import pytest

from bina.application.costs import (
    ITEM_LABELS,
    NOTE,
    CostInput,
    CostItem,
    Heating,
    estimate_costs,
    heating_type,
    month_utilities,
)
from bina.application.localization import script_of


def data(**changes: object) -> CostInput:
    values: dict[str, object] = {
        "rent": Decimal(1500),
        "currency": "GEL",
        "area": 60,
        "features": (),
        "start": date(2026, 11, 1),
    }
    values.update(changes)
    return CostInput(**values)  # type: ignore[arg-type]


def test_heating_type() -> None:
    assert heating_type(()) is Heating.GAS, "удобства не указаны — газ, как обычно в Тбилиси"
    assert heating_type(("furniture", "gas")) is Heating.GAS
    assert heating_type(("heating",)) is Heating.GAS
    assert heating_type(("furniture", "air_conditioning")) is Heating.ELECTRIC


def test_winter_costs_more_than_summer() -> None:
    winter = month_utilities(1, 60, 2, Heating.GAS, air_conditioning=False)
    shoulder = month_utilities(11, 60, 2, Heating.GAS, air_conditioning=False)
    summer = month_utilities(6, 60, 2, Heating.GAS, air_conditioning=False)
    assert summer[CostItem.GAS] < shoulder[CostItem.GAS] < winter[CostItem.GAS]
    assert winter[CostItem.ELECTRICITY] == summer[CostItem.ELECTRICITY]
    electric = month_utilities(1, 60, 2, Heating.ELECTRIC, air_conditioning=False)
    assert electric[CostItem.GAS] == summer[CostItem.GAS]
    assert electric[CostItem.ELECTRICITY] > winter[CostItem.ELECTRICITY]


def test_air_conditioning_and_people() -> None:
    july = month_utilities(7, 60, 2, Heating.GAS, air_conditioning=True)
    june = month_utilities(6, 60, 2, Heating.GAS, air_conditioning=True)
    assert july[CostItem.ELECTRICITY] > june[CostItem.ELECTRICITY]
    four = month_utilities(6, 60, 4, Heating.GAS, air_conditioning=False)
    assert four[CostItem.WATER] == 2 * june[CostItem.WATER]


def test_estimate_totals() -> None:
    estimate = estimate_costs(data(deposit_months=Decimal(1), agency_fee_percent=Decimal(50)))
    assert (estimate.rent, estimate.deposit, estimate.agency_fee) == (Decimal(1500), Decimal(1500), Decimal(750))
    assert len(estimate.months) == 12
    assert [m.month for m in estimate.months[:3]] == [
        date(2026, 11, 1),
        date(2026, 12, 1),
        date(2027, 1, 1),
    ]
    first = estimate.months[0]
    assert estimate.first_month_total == 1500 + 1500 + 750 + first.utilities
    utilities = sum(m.utilities for m in estimate.months)
    assert estimate.period_total == 1500 * 12 + utilities + 750
    assert estimate.average_month == 1500 + estimate.average_utilities
    assert 100 < estimate.average_utilities < 300


def test_currency_and_included_utilities() -> None:
    estimate = estimate_costs(data(rent=Decimal(700), currency="usd", utilities_included=True))
    assert (estimate.rent, estimate.rent_currency) == (Decimal(1890), "USD")
    assert all(m.utilities == 0 and m.items == {} for m in estimate.months)
    assert estimate.period_total == 1890 * 12
    with pytest.raises(ValueError):
        estimate_costs(data(currency="RUB"))


def test_labels_in_every_language() -> None:
    for language in ("ka", "ru", "en"):
        assert script_of(NOTE[language]) == language
        for item in CostItem:
            assert script_of(ITEM_LABELS[item][language]) == language
