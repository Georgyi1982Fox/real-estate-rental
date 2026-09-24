from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.bina.application.repositories.users import IUsersRepository
from src.bina.infrastructure.db.models import User


class UsersRepository(IUsersRepository):
    """Реализация репозитория пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Получить пользователя по ID."""
        query = select(User).where(User.id == user_id, User.is_deleted.is_(False))
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить (не удалённого) пользователя по Telegram ID."""
        query = select(User).where(
            User.telegram_id == telegram_id,
            User.is_deleted.is_(False),
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, telegram_id: int, language: str) -> User:
        """Создать нового пользователя."""
        user = User(telegram_id=telegram_id, language=language)
        self._session.add(user)
        await self._session.flush()  # Получаем ID и серверные значения по умолчанию
        return user

    async def update_language(self, user_id: UUID, language: str) -> None:
        """Обновить язык интерфейса пользователя."""
        query = update(User).where(User.id == user_id).values(language=language)
        await self._session.execute(query)
