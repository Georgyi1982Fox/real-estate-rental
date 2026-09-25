"""Фабрики callback data.

Состояние поиска целиком кодируется в callback data, поэтому кнопки работают
без FSM-хранилища и переживают перезапуск бота. Лимит Telegram: 64 байта.
"""

from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData


class SearchStep(StrEnum):
    """Шаг мастера поиска."""

    DISTRICT = "d"
    PRICE = "p"
    ROOMS = "r"
    RESULTS = "res"


class SearchCallback(CallbackData, prefix="s"):
    """Навигация по мастеру поиска и страницам результатов.

    ``price`` и ``rooms``: индексы пресетов из :mod:`.filters`, ``None``: «любые».
    ``page``: страница списка районов на шаге DISTRICT и страница результатов на RESULTS.
    """

    step: SearchStep
    district: UUID | None = None
    price: int | None = None
    rooms: int | None = None
    page: int = 0


class FavoriteToggleCallback(CallbackData, prefix="fav"):
    """Добавить объявление в избранное или убрать из него."""

    listing_id: UUID


class FavoritesPageCallback(CallbackData, prefix="favp"):
    """Страница избранного."""

    page: int


class LanguageCallback(CallbackData, prefix="lang"):
    """Смена языка интерфейса."""

    code: str


class NoopCallback(CallbackData, prefix="noop"):
    """Неактивная кнопка (счётчик страниц)."""
