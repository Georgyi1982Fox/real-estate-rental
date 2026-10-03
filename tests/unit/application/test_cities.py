"""Города (TASK-079)."""

import pytest

from bina.application.cities import CITIES, city_name, city_of, in_city, parse_cities
from bina.application.district_guide import guide_for, minutes_to_center
from bina.infrastructure.api.routes.searches import default_search_name
from bina.infrastructure.api.schemas import SearchFiltersIn


def test_all_georgian_cities_present() -> None:
    # Главные города плюс курорты (TASK-079: вся Грузия)
    for code in ("tbilisi", "batumi", "kutaisi", "rustavi", "kobuleti", "gori"):
        assert code in CITIES


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Батуми", "batumi"),
        ("ბათუმი", "batumi"),
        ("batumi", "batumi"),
        ("Тбилиси", "tbilisi"),
        ("Кутаиси", "kutaisi"),
        ("ქუთაისი", "kutaisi"),
        ("Рустави", "rustavi"),
        ("", None),
        ("Париж", None),
    ],
)
def test_city_of(name: str, expected: str | None) -> None:
    assert city_of(name) == expected


def test_city_of_ss_ids() -> None:
    assert city_of(ss_city_id=95) == "tbilisi"
    assert city_of(ss_city_id=96) == "batumi"
    assert city_of("Батуми", ss_city_id=1) == "batumi"


def test_bounds_and_center() -> None:
    assert in_city(41.6485, 41.6380, "batumi")
    assert not in_city(41.6485, 41.6380, "tbilisi")
    assert city_name("batumi", "ka") == "ბათუმი"
    # Старый Батуми рядом с площадью Европы, а не в 350 км от площади Свободы
    old = guide_for("Old Batumi", "batumi")
    assert old is not None
    assert minutes_to_center(old.latitude, old.longitude, "batumi") <= 10
    assert guide_for("Old Batumi") is None, "справка Батуми не путается с Тбилиси"


def test_parse_cities() -> None:
    assert parse_cities("tbilisi, Batumi") == ("tbilisi", "batumi")
    # Пусто или "all" — все города Грузии (TASK-079)
    assert parse_cities("") == tuple(CITIES)
    assert parse_cities("all") == tuple(CITIES)
    assert parse_cities("tbilisi,kutaisi") == ("tbilisi", "kutaisi")
    with pytest.raises(ValueError, match="paris"):
        parse_cities("tbilisi,paris")


def test_saved_search_name_with_city() -> None:
    filters = SearchFiltersIn(city="batumi", rooms=2)
    assert default_search_name(filters, [], "ru") == "Батуми, 2 комн."
