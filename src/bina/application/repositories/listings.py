from abc import ABC, abstractmethod
from typing import Protocol
from uuid import UUID

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.infrastructure.db.models import Listing


class IListingsRepository(Protocol):
    """Порт репозитория объявлений."""

    @abstractmethod
    async def get_active_listings_by_district(
        self,
        district_id: UUID,
        limit: int,
    ) -> list[Listing]:
        """Получить активные объявления по району."""
        ...
    
    @abstractmethod
    async def get_by_id(self, listing_id: UUID) -> Listing | None:
        """Получить объявление по ID."""
        ...
    
    @abstractmethod
    async def find_by_source(
        self,
        source_id: str,
        source_name: str,
    ) -> Listing | None:
        """Найти объявление по source_id и source_name."""
        ...
    
    @abstractmethod
    async def save_translation(
        self,
        listing_id: UUID,
        title_ru: str,
        description_ru: str,
    ) -> None:
        """Сохранить перевод объявления."""
        ...
    
    @abstractmethod
    async def search(
        self,
        filters: ListingSearchFilters,
        limit: int,
        offset: int = 0,
    ) -> list[Listing]:
        """Найти активные объявления по фильтрам (новые сверху)."""
        ...

    @abstractmethod
    async def count(self, filters: ListingSearchFilters) -> int:
        """Количество активных объявлений, подходящих под фильтры."""
        ...

    @abstractmethod
    async def create_or_update_from_raw(
        self,
        raw_listing: "RawListing",  # type: ignore[name-defined]
    ) -> Listing:
        """Создать или обновить объявление из RawListing."""
        ...