from abc import ABC, abstractmethod
from typing import Protocol
from uuid import UUID

from src.bina.infrastructure.db.models import Listing


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