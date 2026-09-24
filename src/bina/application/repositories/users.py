from abc import abstractmethod
from typing import Protocol
from uuid import UUID

from src.bina.infrastructure.db.models import User


class IUsersRepository(Protocol):
    """Порт репозитория пользователей."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Получить пользователя по ID."""
        ...

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить (не удалённого) пользователя по Telegram ID."""
        ...

    @abstractmethod
    async def create(self, telegram_id: int, language: str) -> User:
        """Создать нового пользователя."""
        ...

    @abstractmethod
    async def update_language(self, user_id: UUID, language: str) -> None:
        """Обновить язык интерфейса пользователя."""
        ...
