from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bina.application.repositories.districts import IDistrictsRepository
from src.bina.infrastructure.db.models import District

if TYPE_CHECKING:
    from collections.abc import Sequence


class DistrictsRepository(IDistrictsRepository):
    """Реализация репозитория районов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> District | None:
        """Получить район по названию."""
        # Пытаемся найти по грузинскому или русскому названию
        query = select(District).where(
            (District.name_ka == name) | (District.name_ru == name)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create_district(self, name: str) -> District:
        """Создать новый район."""
        # Создаем район с одинаковым названием на всех языках
        new_district = District(
            name_ka=name,
            name_ru=name,
        )
        self._session.add(new_district)
        await self._session.flush()
        return new_district