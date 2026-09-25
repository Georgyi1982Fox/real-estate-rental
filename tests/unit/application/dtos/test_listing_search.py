from decimal import Decimal

import pytest
from pydantic import ValidationError

from bina.application.dtos.listing_search import ListingSearchFilters


def test_defaults_are_unbounded() -> None:
    """По умолчанию фильтры ничего не ограничивают."""
    filters = ListingSearchFilters()
    assert filters.district_id is None
    assert filters.price_min is None
    assert filters.rooms_max is None


def test_open_ranges_allowed() -> None:
    """Допускаются полуоткрытые диапазоны («4+ комнаты»)."""
    filters = ListingSearchFilters(rooms_min=4, price_min=Decimal("2000"))
    assert filters.rooms_min == 4
    assert filters.rooms_max is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"price_min": Decimal("2000"), "price_max": Decimal("1000")},
        {"rooms_min": 3, "rooms_max": 1},
    ],
)
def test_inverted_ranges_rejected(kwargs: dict[str, object]) -> None:
    """Нижняя граница не может превышать верхнюю."""
    with pytest.raises(ValidationError):
        ListingSearchFilters(**kwargs)  # type: ignore[arg-type]


def test_filters_are_immutable() -> None:
    """Фильтры неизменяемы (безопасно хранить в FSM)."""
    filters = ListingSearchFilters()
    with pytest.raises(ValidationError):
        filters.rooms_min = 2
