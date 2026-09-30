"""Вид аренды (TASK-092)."""

import pytest

from bina.application.rent_period import DAILY, MONTHLY, period_from_text, rent_period_code
from bina.application.saved_searches import detail_filters
from bina.infrastructure.api.routes.searches import default_search_name
from bina.infrastructure.api.schemas import SearchFiltersIn


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("квартира посуточно в Ваке", DAILY),
        ("Сдам на сутки у моря", DAILY),
        ("apartment for daily rent in Batumi", DAILY),
        ("ბინა დღიურად ბათუმში", DAILY),
        ("светлая квартира с балконом рядом с метро", MONTHLY),
        ("2 bedroom flat in Saburtalo", MONTHLY),
    ],
)
def test_period_from_text(text: str, expected: str) -> None:
    assert period_from_text(text) == expected


def test_rent_period_code() -> None:
    assert rent_period_code("daily") == DAILY
    assert rent_period_code("weekly") == MONTHLY
    assert rent_period_code(None) == MONTHLY


def test_saved_search_with_daily_rent() -> None:
    daily = SearchFiltersIn(city="batumi", rent_period="daily", rooms=1)
    assert default_search_name(daily, [], "ru") == "Батуми, посуточно, 1 комн."
    assert daily.details() == {"city": "batumi", "rent_period": "daily"}
    assert detail_filters(daily.details())["rent_period"] == "daily"
    assert "rent_period" not in SearchFiltersIn(rooms=1).details(), "помесячно — по умолчанию"
    assert "rent_period" not in detail_filters({})
