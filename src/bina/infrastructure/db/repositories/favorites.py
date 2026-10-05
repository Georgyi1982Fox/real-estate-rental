from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.repositories.favorites import IFavoritesRepository
from bina.infrastructure.db.models import Favorite, Listing


class FavoritesRepository(IFavoritesRepository):
    """Реализация репозитория избранных объявлений."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: UUID, listing_id: UUID) -> None:
        """Добавить объявление в избранное (идемпотентно)."""
        query = (
            insert(Favorite)
            .values(user_id=user_id, listing_id=listing_id)
            .on_conflict_do_nothing(index_elements=["user_id", "listing_id"])
        )
        await self._session.execute(query)

    async def remove(self, user_id: UUID, listing_id: UUID) -> bool:
        """Удалить объявление из избранного. Возвращает True, если запись была."""
        query = (
            delete(Favorite)
            .where(Favorite.user_id == user_id, Favorite.listing_id == listing_id)
            .returning(Favorite.listing_id)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none() is not None

    async def exists(self, user_id: UUID, listing_id: UUID) -> bool:
        """Проверить, находится ли объявление в избранном."""
        query = select(Favorite.listing_id).where(
            Favorite.user_id == user_id,
            Favorite.listing_id == listing_id,
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none() is not None

    async def filter_favorite_ids(
        self,
        user_id: UUID,
        listing_ids: Sequence[UUID],
    ) -> set[UUID]:
        """Вернуть подмножество ``listing_ids``, которые есть в избранном."""
        if not listing_ids:
            return set()
        query = select(Favorite.listing_id).where(
            Favorite.user_id == user_id,
            Favorite.listing_id.in_(listing_ids),
        )
        result = await self._session.execute(query)
        return set(result.scalars().all())

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int,
        offset: int = 0,
    ) -> list[Listing]:
        """Получить избранные объявления пользователя (новые сверху).

        Удалённые объявления не возвращаются.
        """
        query = (
            select(Listing)
            .join(Favorite, Favorite.listing_id == Listing.id)
            .where(Favorite.user_id == user_id, Listing.is_deleted.is_(False))
            .order_by(Favorite.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_ids(self, user_id: UUID, limit: int) -> list[UUID]:
        """ID избранных объявлений пользователя (новые сверху, удалённые не возвращаются)."""
        query = (
            select(Favorite.listing_id)
            .join(Listing, Favorite.listing_id == Listing.id)
            .where(Favorite.user_id == user_id, Listing.is_deleted.is_(False))
            .order_by(Favorite.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: UUID) -> int:
        """Количество избранных объявлений пользователя."""
        query = (
            select(func.count())
            .select_from(Favorite)
            .join(Listing, Favorite.listing_id == Listing.id)
            .where(Favorite.user_id == user_id, Listing.is_deleted.is_(False))
        )
        result = await self._session.execute(query)
        return int(result.scalar_one())

    # TASK-074: заметки

    async def notes(self, user_id: UUID, listing_ids: list[UUID] | None = None) -> dict[UUID, str]:
        """Непустые заметки к избранному (все или только для ``listing_ids``)."""
        query = select(Favorite.listing_id, Favorite.note).where(
            Favorite.user_id == user_id, Favorite.note != ""
        )
        if listing_ids is not None:
            query = query.where(Favorite.listing_id.in_(listing_ids))
        return {row.listing_id: row.note for row in await self._session.execute(query)}

    async def set_note(self, user_id: UUID, listing_id: UUID, note: str) -> bool:
        """Сохранить заметку; ``False`` — квартиры нет в избранном."""
        result = await self._session.execute(
            update(Favorite)
            .where(Favorite.user_id == user_id, Favorite.listing_id == listing_id)
            .values(note=note)
            .returning(Favorite.listing_id)
        )
        return result.first() is not None
