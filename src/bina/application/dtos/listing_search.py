"""DTO фильтров поиска объявлений."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class ListingSearchFilters(BaseModel):
    """Фильтры поиска активных объявлений.

    Поле, равное ``None``, не ограничивает выборку.
    Границы диапазонов включительные.
    """

    model_config = ConfigDict(frozen=True)

    district_id: UUID | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    rooms_min: int | None = None
    rooms_max: int | None = None

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
        return self
