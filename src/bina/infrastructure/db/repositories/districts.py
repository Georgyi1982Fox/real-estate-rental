from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.cities import CITIES, DEFAULT_CITY
from bina.application.localization import district_base, district_names
from bina.application.repositories.districts import IDistrictsRepository
from bina.infrastructure.db.models import District, Listing, SavedSearch

if TYPE_CHECKING:
    pass


class DistrictsRepository(IDistrictsRepository):
    """Реализация репозитория районов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(
        self, name: str, city: str = DEFAULT_CITY, *, active_only: bool = False
    ) -> District | None:
        """Получить район города по названию на любом языке (``active_only`` — без скрытых)."""
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
        if active_only:
            query = query.where(District.is_deleted.is_(False))
        result = await self._session.execute(query)
        return result.scalars().first()

    async def find(self, name: str, city: str = DEFAULT_CITY) -> District | None:
        """Район города по названию с сайта: и по словарным написаниям («Старий Тбилиси»)."""
        for candidate in dict.fromkeys([name, *district_names(name).values()]):
            district = await self.get_by_name(candidate, city, active_only=True)
            if district is not None:
                return district
        return None

    async def merge_streets(self) -> int:
        """Склеить «районы» вида «Сабуртало/Картозия» с настоящим районом «Сабуртало».

        Объявления и сохранённые поиски переходят в настоящий район (его нет — создаётся),
        «район с улицей» скрывается. Возвращает, сколько таких районов склеено.
        """
        names = (District.name_ru, District.name_ka, District.name_en)
        query = select(District).where(
            District.is_deleted.is_(False),
            or_(*(column.contains(mark) for column in names for mark in ("/", ","))),
        )
        merged = 0
        for junk in (await self._session.execute(query)).scalars().all():
            base = next(
                (
                    found
                    for name in (junk.name_ru, junk.name_ka, junk.name_en)
                    if (found := district_base(name))
                ),
                None,
            )
            if base is None:
                continue
            target = await self.find(base, junk.city)
            if target is None or target.id == junk.id:
                target = await self.create_district(base, junk.city)
            await self._move(junk.id, target.id)
            junk.is_deleted = True
            merged += 1
        await self._session.flush()
        return merged

    async def _move(self, old_id: UUID, new_id: UUID) -> None:
        """Перенести объявления и сохранённые поиски из района ``old_id`` в ``new_id``."""
        await self._session.execute(
            update(Listing).where(Listing.district_id == old_id).values(district_id=new_id)
        )
        await self._session.execute(
            update(SavedSearch).where(SavedSearch.district_id == old_id).values(district_id=new_id)
        )
        await self._session.execute(
            update(SavedSearch)
            .where(SavedSearch.district_ids.contains([old_id]))
            .values(district_ids=func.array_replace(SavedSearch.district_ids, old_id, new_id))
        )

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

    async def cities_of(self, district_ids: list[UUID]) -> dict[UUID, str]:
        """Город каждого района (TASK-076)."""
        if not district_ids:
            return {}
        query = select(District.id, District.city).where(District.id.in_(district_ids))
        return {row.id: row.city for row in await self._session.execute(query)}

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
