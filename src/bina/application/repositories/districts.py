from abc import ABC, abstractmethod
from typing import Protocol
from uuid import UUID

from src.bina.infrastructure.db.models import District


class IDistrictsRepository(Protocol):
    """Порт репозитория районов."""

    @abstractmethod
    async def get_by_name(self, name: str) -> District | None:
        """Получить район по названию."""
        ...
    
    @abstractmethod
    async def get_by_id(self, district_id: UUID) -> District | None:
        """Получить район по ID."""
        ...

    @abstractmethod
    async def list_all(self) -> list[District]:
        """Получить все (не удалённые) районы, отсортированные по названию."""
        ...

    @abstractmethod
    async def create_district(self, name: str) -> District:
        """Создать новый район."""
        ...