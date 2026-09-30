"""DTO фильтров поиска объявлений."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from bina.application.rent_period import MONTHLY


class ListingSort(StrEnum):
    """Порядок выдачи объявлений (параметр ``sort`` API)."""

    NEWEST = "newest"
    # По совпадению с текстом поиска (без текста — как newest)
    RELEVANCE = "relevance"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    AREA_DESC = "area_desc"
    PRICE_PER_M2_ASC = "price_per_m2_asc"
    # TASK-012: по смыслу текста поиска (embeddings); без текста — как newest
    SMART = "smart"


# Источники объявлений (Listing.source_name)
SOURCES: tuple[str, ...] = ("ss", "myhome", "livo", "korter", "telegram")


class ListingSearchFilters(BaseModel):
    """Фильтры поиска активных объявлений.

    Поле, равное ``None``, не ограничивает выборку.
    Границы диапазонов включительные.
    """

    model_config = ConfigDict(frozen=True)

    # Город (``bina.application.cities``); None — все города (TASK-079)
    city: str | None = None
    # Вид аренды (TASK-092): по умолчанию помесячно — цены посуточной аренды за сутки
    # и в одном списке с помесячными сбивают с толку; None — любой
    rent_period: str | None = MONTHLY
    district_id: UUID | None = None
    # Несколько районов (любой из них); вместе с district_id — объединение
    district_ids: tuple[UUID, ...] = ()
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    rooms_min: int | None = None
    rooms_max: int | None = None
    area_min: Decimal | None = None
    area_max: Decimal | None = None
    # Текст поиска: заголовок и описание на ru/ka/en (TASK-022)
    query: str | None = None
    # TASK-018: подробности со страницы объявления
    floor_min: int | None = None
    floor_max: int | None = None
    not_first_floor: bool = False
    not_last_floor: bool = False
    bedrooms_min: int | None = None
    bathrooms_min: int | None = None
    # Есть все удобства из списка (коды listing_details.FEATURES)
    features: tuple[str, ...] = ()
    # Любое из состояний (коды listing_details.CONDITIONS)
    conditions: tuple[str, ...] = ()
    # Только собственники, без агентств
    owner_only: bool = False
    # Опубликовано на сайте не раньше
    published_since: datetime | None = None
    # Источники (любой из): ss, myhome, livo, korter, telegram (SOURCES)
    sources: tuple[str, ...] = ()

    @property
    def all_district_ids(self) -> list[UUID]:
        """Все районы фильтра без повторов (пусто — любой район)."""
        ids = [*self.district_ids, *([self.district_id] if self.district_id else [])]
        return list(dict.fromkeys(ids))

    @model_validator(mode="after")
    def _check_ranges(self) -> "ListingSearchFilters":
        """Проверяет, что нижняя граница не превышает верхнюю."""
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("price_min must be <= price_max")
        if (
            self.rooms_min is not None
            and self.rooms_max is not None
            and self.rooms_min > self.rooms_max
        ):
            raise ValueError("rooms_min must be <= rooms_max")
        if (
            self.area_min is not None
            and self.area_max is not None
            and self.area_min > self.area_max
        ):
            raise ValueError("area_min must be <= area_max")
        if (
            self.floor_min is not None
            and self.floor_max is not None
            and self.floor_min > self.floor_max
        ):
            raise ValueError("floor_min must be <= floor_max")
        return self


# «4» в фильтре комнат (Mini App, сохранённые поиски) означает «4 и больше»
ROOMS_OR_MORE = 4


def search_filters(
    district_id: UUID | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    rooms: int | None = None,
    area_min: Decimal | None = None,
    area_max: Decimal | None = None,
    query: str | None = None,
    district_ids: Sequence[UUID] = (),
    **details: Any,
) -> ListingSearchFilters:
    """Фильтры из параметров Mini App: ``rooms`` — точное число, 4 — «4 и больше».

    Raises:
        pydantic.ValidationError: если нижняя граница цены или площади больше верхней.
    """
    return ListingSearchFilters(
        district_id=district_id,
        district_ids=tuple(district_ids),
        price_min=price_min,
        price_max=price_max,
        rooms_min=rooms,
        rooms_max=None if rooms is None or rooms >= ROOMS_OR_MORE else rooms,
        area_min=area_min,
        area_max=area_max,
        query=(query or "").strip() or None,
        **details,
    )
