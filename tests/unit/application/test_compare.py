"""Сравнение квартир (TASK-105): отметка лучших значений."""

from decimal import Decimal
from uuid import UUID, uuid4

from bina.application.compare import ROWS, ComparedValues, best_in_rows
from bina.application.localization import script_of


def item(**changes: object) -> ComparedValues:
    values: dict[str, object] = {
        "listing_id": uuid4(),
        "price": Decimal(1500),
        "price_per_m2": Decimal(25),
        "area": 60.0,
        "minutes_to_center": 15,
        "move_in": Decimal(3200),
        "average_month": Decimal(1700),
        "features": 3,
        "risk_level": "none",
    }
    values.update(changes)
    return ComparedValues(**values)  # type: ignore[arg-type]


def test_best_values() -> None:
    cheap = item(price=Decimal(1200), price_per_m2=Decimal(30), area=40.0, risk_level="warning")
    big = item(area=90.0, price_per_m2=Decimal("16.7"), features=6, minutes_to_center=None)
    best = best_in_rows([cheap, big])

    def ids(*items: ComparedValues) -> list[UUID]:
        return [value.listing_id for value in items]

    assert best["price"] == ids(cheap)
    assert best["price_per_m2"] == ids(big)
    assert best["area"] == ids(big)
    assert best["features"] == ids(big)
    assert best["risk_level"] == ids(big)
    # Время до центра известно только у одной — не сравниваем; одинаковое — не отмечаем
    assert "minutes_to_center" not in best
    assert "move_in" not in best


def test_ties_are_all_marked() -> None:
    a, b, c = item(price=Decimal(1000)), item(price=Decimal(1000)), item(price=Decimal(1400))
    assert best_in_rows([a, b, c])["price"] == [a.listing_id, b.listing_id]


def test_row_titles_in_every_language() -> None:
    for labels in ROWS.values():
        for language in ("ka", "ru", "en"):
            assert script_of(labels[language]) == language
