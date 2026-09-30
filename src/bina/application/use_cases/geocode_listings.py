"""Точки на карте для объявлений без координат (TASK-080).

С SS.ge и MyHome.ge координаты приходят сами; у объявлений из Telegram-каналов
есть только адрес — его ищем через геокодер. Точка вне города объявления
(Тбилиси, Батуми) считается ошибкой.
Не найдено — отмечаем, чтобы не искать заново; карта покажет центр района.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import structlog

from bina.application.cities import DEFAULT_CITY, in_city
from bina.application.ports.geocoder import GeocoderError, IGeocoder
from bina.infrastructure.db.models import Listing

logger = structlog.get_logger(__name__)


class IGeocodeRepository(Protocol):
    async def to_geocode(self, limit: int) -> list[Listing]: ...

    async def save_location(
        self, listing_id: UUID, location: tuple[float, float] | None
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class GeocodeStats:
    checked: int
    found: int
    failed: int


class GeocodeListingsUseCase:
    """Ищет адреса на карте. Не коммитит."""

    def __init__(self, listings: IGeocodeRepository, geocoder: IGeocoder) -> None:
        self._listings = listings
        self._geocoder = geocoder

    async def execute(self, limit: int) -> GeocodeStats:
        checked = found = failed = 0
        for listing in await self._listings.to_geocode(limit):
            city = listing.district.city if listing.district else DEFAULT_CITY
            try:
                location = await self._geocoder.locate(listing.address or "", city)
            except GeocoderError:
                # Сервис не ответил — не отмечаем, попробуем при следующем запуске
                failed += 1
                logger.warning("Geocoding failed", listing_id=str(listing.id))
                continue
            if location is not None and not in_city(*location, city):
                location = None
            await self._listings.save_location(listing.id, location)
            checked += 1
            found += location is not None
        return GeocodeStats(checked=checked, found=found, failed=failed)
