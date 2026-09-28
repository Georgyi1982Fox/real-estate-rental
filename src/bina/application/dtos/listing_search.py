"""DTO фильтров поиска объявлений."""

from collections.abc import Sequence
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class ListingSort(StrEnum):
    """Порядок выдачи объявлений (параметр ``sort`` API)."""

    NEWEST = "newest"
    # По совпадению с текстом поиска (без текста — как newest)
    RELEVANCE = "relevance"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    AREA_DESC = "area_desc"
    PRICE_PER_M2_ASC = "price_per_m2_asc"


class ListingSearchFilters(BaseModel):
    """Фильтры поиска активных объявлений.

    Поле, равное ``None``, не ограничивает выборку.
    Границы диапазонов включительные.
    """

    model_config = ConfigDict(frozen=True)

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
    )
