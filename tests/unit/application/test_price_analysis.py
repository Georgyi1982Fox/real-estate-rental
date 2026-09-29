"""Анализ цены (TASK-093): полоса «обычной цены» ±10%."""

from decimal import Decimal

import pytest

from bina.application.price_analysis import (
    PriceBasis,
    PriceLevel,
    compare_price,
    rooms_group,
)

ROOMS = PriceBasis.DISTRICT_ROOMS


@pytest.mark.parametrize(
    ("price", "level", "diff"),
    [
        (Decimal(800), PriceLevel.BELOW, -20),
        (Decimal(905), PriceLevel.FAIR, -10),  # ровно на границе — ещё обычная
        (Decimal(1000), PriceLevel.FAIR, 0),
        (Decimal(1100), PriceLevel.FAIR, 10),
        (Decimal(1150), PriceLevel.ABOVE, 15),
    ],
)
def test_compare_price(price: Decimal, level: PriceLevel, diff: int) -> None:
    result = compare_price(price, Decimal(1000), 8, ROOMS)
    assert (result.level, result.diff_percent) == (level, diff)
    assert (result.typical_price, result.sample, result.basis) == (Decimal(1000), 8, ROOMS)


def test_unknown_without_data() -> None:
    assert compare_price(Decimal(800), Decimal(1000), 4, ROOMS).level is PriceLevel.UNKNOWN
    assert compare_price(Decimal(800), Decimal(0), 10, ROOMS).level is PriceLevel.UNKNOWN


def test_typical_price_rounded() -> None:
    result = compare_price(Decimal(700), Decimal("1234.567"), 6, PriceBasis.DISTRICT_M2)
    assert result.typical_price == Decimal(1235)


def test_rooms_group() -> None:
    assert [rooms_group(n) for n in (1, 2, 3, 4, 5, 7)] == [1, 2, 3, 4, 4, 4]
