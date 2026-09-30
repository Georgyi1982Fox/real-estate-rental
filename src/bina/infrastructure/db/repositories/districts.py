from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.cities import CITIES, DEFAULT_CITY
from bina.application.localization import district_names
from bina.application.repositories.districts import IDistrictsRepository
from bina.infrastructure.db.models import District

if TYPE_CHECKING:
    pass


class DistrictsRepository(IDistrictsRepository):
    """Реализация репозитория районов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str, city: str = DEFAULT_CITY) -> District | None:
        """Получить район города по названию на любом языке."""
        query = (
            select(District)
            .where(
                District.city == city,
                (District.name_ka == name)
                | (District.name_ru == name)
                | (District.name_en == name),
            )
            .order_by(District.created_at)
        )
        result = await self._session.execute(query)
        return result.scalars().first()

    async def get_by_id(self, district_id: UUID) -> District | None:
        """Получить район по ID."""
        query = select(District).where(District.id == district_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self, city: str | None = None) -> list[District]:
        """Все (не удалённые) районы города (``None`` — всех городов) по названию."""
        query = select(District).where(District.is_deleted.is_(False)).order_by(District.name_ru)
        if city is not None:
            query = query.where(District.city == city)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def cities(self) -> list[str]:
        """Коды городов, в которых есть районы (TASK-079)."""
        query = select(District.city).where(District.is_deleted.is_(False)).distinct()
        found = set((await self._session.execute(query)).scalars().all())
        return [code for code in CITIES if code in found]

    async def create_district(self, name: str, city: str = DEFAULT_CITY) -> District:
        """Создать новый район."""
        # Названия на трёх языках: словарь районов Тбилиси, иначе транслитерация (TASK-019);
        # статистика района пока неизвестна
        names = district_names(name) or {"ka": name, "ru": name, "en": name}
        new_district = District(
            city=city,
            name_ka=names["ka"],
            name_ru=names["ru"],
            name_en=names["en"],
            avg_price_per_m2=0,
            safety_score=0,
        )
        self._session.add(new_district)
        await self._session.flush()
        return new_district
