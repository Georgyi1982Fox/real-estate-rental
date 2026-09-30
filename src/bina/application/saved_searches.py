"""Фильтры сохранённого поиска (TASK-028, TASK-086).

Район, цена и комнаты хранятся в колонках поиска, остальные фильтры — в
``details`` (JSON) под именами полей :class:`ListingSearchFilters`.
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from bina.application.dtos.listing_search import ListingSearchFilters, search_filters
from bina.infrastructure.db.models import SavedSearch

# Какие поля ListingSearchFilters сохраняются в details
DETAIL_FIELDS: tuple[str, ...] = (
    "city",
    "area_min",
    "area_max",
    "query",
    "floor_min",
    "floor_max",
    "not_first_floor",
    "not_last_floor",
    "bedrooms_min",
    "bathrooms_min",
    "features",
    "conditions",
    "owner_only",
)
_DECIMALS = ("area_min", "area_max")
_LISTS = ("features", "conditions")


def detail_filters(details: Mapping[str, Any] | None) -> dict[str, Any]:
    """Поля ``ListingSearchFilters`` из JSON поиска (неизвестные ключи отбрасываются)."""
    values = {key: value for key, value in (details or {}).items() if key in DETAIL_FIELDS}
    for key in _DECIMALS:
        if values.get(key) is not None:
            values[key] = Decimal(str(values[key]))
    for key in _LISTS:
        if key in values:
            values[key] = tuple(values[key] or ())
    return values


def saved_search_filters(search: SavedSearch) -> ListingSearchFilters:
    """Фильтры, по которым ищутся квартиры сохранённого поиска."""
    return search_filters(
        district_ids=search.all_district_ids,
        price_min=search.price_min,
        price_max=search.price_max,
        rooms=search.rooms,
        **detail_filters(search.details),
    )
