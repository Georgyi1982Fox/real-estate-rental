from abc import abstractmethod
from typing import Protocol
from uuid import UUID

from bina.application.cities import DEFAULT_CITY
from bina.infrastructure.db.models import District


class IDistrictsRepository(Protocol):
    """Порт репозитория районов."""

    @abstractmethod
    async def get_by_name(self, name: str, city: str = DEFAULT_CITY) -> District | None:
        """Получить район города по названию."""
        ...

    @abstractmethod
    async def get_by_id(self, district_id: UUID) -> District | None:
        """Получить район по ID."""
        ...

    @abstractmethod
    async def list_all(self, city: str | None = None) -> list[District]:
        """Все (не удалённые) районы города (``None`` — всех городов) по названию."""
        ...

    @abstractmethod
    async def cities(self) -> list[str]:
        """Коды городов, в которых есть районы."""
        ...

    @abstractmethod
    async def create_district(self, name: str, city: str = DEFAULT_CITY) -> District:
        """Создать новый район."""
        ...
