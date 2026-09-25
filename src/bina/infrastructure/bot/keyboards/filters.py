"""Пресеты фильтров поиска: диапазоны цен и количество комнат."""

from dataclasses import dataclass
from decimal import Decimal

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.infrastructure.bot.formatters import format_number
from bina.infrastructure.bot.keyboards.callbacks import SearchCallback
from bina.infrastructure.bot.texts import t


@dataclass(frozen=True, slots=True)
class Range:
    """Диапазон значений; ``None`` означает открытую границу."""

    min: int | None
    max: int | None


# Цены в GEL: нормализатор парсера приводит все цены к лари
PRICE_RANGES: tuple[Range, ...] = (
    Range(None, 1000),
    Range(1000, 1500),
    Range(1500, 2500),
    Range(2500, 4000),
    Range(4000, None),
)

ROOM_OPTIONS: tuple[Range, ...] = (
    Range(1, 1),
    Range(2, 2),
    Range(3, 3),
    Range(4, None),
)


def _preset(options: tuple[Range, ...], index: int | None) -> Range | None:
    """Пресет по индексу; неизвестный индекс трактуется как «любой»."""
    if index is None or not 0 <= index < len(options):
        return None
    return options[index]


def price_label(index: int | None, language: str) -> str:
    """Подпись диапазона цен."""
    preset = _preset(PRICE_RANGES, index)
    if preset is None:
        return t(language, "any_price")
    if preset.min is None and preset.max is not None:
        return t(language, "price_up_to", max=format_number(preset.max))
    if preset.max is None and preset.min is not None:
        return t(language, "price_from", min=format_number(preset.min))
    return t(
        language,
        "price_between",
        min=format_number(preset.min or 0),
        max=format_number(preset.max or 0),
    )


def rooms_button_label(index: int | None, language: str) -> str:
    """Короткая подпись кнопки комнат: ``2``, ``4+``."""
    preset = _preset(ROOM_OPTIONS, index)
    if preset is None or preset.min is None:
        return t(language, "any_rooms")
    key = "rooms_exact" if preset.min == preset.max else "rooms_from"
    return t(language, key, n=preset.min)


def rooms_label(index: int | None, language: str) -> str:
    """Подпись фильтра комнат в заголовке: ``2 комн.``, ``Любое``."""
    if _preset(ROOM_OPTIONS, index) is None:
        return t(language, "any_rooms")
    return t(language, "rooms_label", value=rooms_button_label(index, language))


def filters_from_callback(callback_data: SearchCallback) -> ListingSearchFilters:
    """Строит фильтры поиска из callback data."""
    price = _preset(PRICE_RANGES, callback_data.price)
    rooms = _preset(ROOM_OPTIONS, callback_data.rooms)
    return ListingSearchFilters(
        district_id=callback_data.district,
        price_min=Decimal(price.min) if price and price.min is not None else None,
        price_max=Decimal(price.max) if price and price.max is not None else None,
        rooms_min=rooms.min if rooms else None,
        rooms_max=rooms.max if rooms else None,
    )
