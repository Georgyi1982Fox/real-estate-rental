"""«Открыть в приложении» под результатами поиска открывает тот же поиск на сайте."""

from decimal import Decimal
from uuid import UUID

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.rent_period import DAILY
from bina.infrastructure.bot.keyboards.callbacks import SearchCallback, SearchStep
from bina.infrastructure.bot.keyboards.filters import filters_from_callback
from bina.infrastructure.bot.keyboards.menu import mini_app_search_url

APP = "https://bina.example"
VAKE = UUID(int=7)


def test_no_filters_opens_home() -> None:
    assert mini_app_search_url(APP, ListingSearchFilters()) == APP


def test_filters_go_into_the_address() -> None:
    filters = ListingSearchFilters(
        district_id=VAKE, price_min=Decimal(500), price_max=Decimal(1000), rooms_min=2, rooms_max=2
    )
    assert mini_app_search_url(APP, filters) == (
        f"{APP}?district={VAKE}&min_price=500&max_price=1000&rooms=2"
    )


def test_many_rooms_and_daily() -> None:
    filters = ListingSearchFilters(rooms_min=5, rent_period=DAILY)
    assert mini_app_search_url(f"{APP}/?lang=ka", filters) == (
        f"{APP}/?lang=ka&rooms=4&rent_period=daily"
    )


def test_rooms_range_is_not_sent() -> None:
    filters = ListingSearchFilters(rooms_min=1, rooms_max=2)
    assert mini_app_search_url(APP, filters) == APP


def test_bot_search_preset_round_trip() -> None:
    query = SearchCallback(step=SearchStep.RESULTS, district=VAKE, price=0, rooms=1)
    url = mini_app_search_url(APP, filters_from_callback(query))
    assert url.startswith(f"{APP}?district={VAKE}")
    assert "max_price=" in url
