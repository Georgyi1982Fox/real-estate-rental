from abc import abstractmethod
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.bina.infrastructure.db.models import Listing


class IFavoritesRepository(Protocol):
    """Порт репозитория избранных объявлений."""

    @abstractmethod
    async def add(self, user_id: UUID, listing_id: UUID) -> None:
        """Добавить объявление в избранное (идемпотентно)."""
        ...

    @abstractmethod
    async def remove(self, user_id: UUID, listing_id: UUID) -> bool:
        """Удалить объявление из избранного. Возвращает True, если запись была."""
        ...

    @abstractmethod
    async def exists(self, user_id: UUID, listing_id: UUID) -> bool:
        """Проверить, находится ли объявление в избранном."""
        ...

    @abstractmethod
    async def filter_favorite_ids(
        self,
        user_id: UUID,
        listing_ids: Sequence[UUID],
    ) -> set[UUID]:
        """Вернуть подмножество ``listing_ids``, которые есть в избранном."""
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int = 0,
    ) -> list[Listing]:
        """Получить избранные объявления пользователя (новые сверху)."""
        ...

    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int:
        """Количество избранных объявлений пользователя."""
        ...
