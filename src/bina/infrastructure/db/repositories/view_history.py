"""«Недавно смотрели» (TASK-075)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.models import Listing, ViewedListing

# Сколько последних просмотров храним на человека
KEEP = 100


class ViewHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, user_id: UUID, listing_id: UUID, now: datetime) -> None:
        """Отметить просмотр (повторный — просто обновляет время) и забыть старые сверх KEEP."""
        statement = pg_insert(ViewedListing).values(
            user_id=user_id, listing_id=listing_id, viewed_at=now
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[ViewedListing.user_id, ViewedListing.listing_id],
                set_={"viewed_at": now},
            )
        )
        newest = (
            select(ViewedListing.listing_id)
            .where(ViewedListing.user_id == user_id)
            .order_by(ViewedListing.viewed_at.desc())
            .limit(KEEP)
        )
        await self._session.execute(
            delete(ViewedListing).where(
                ViewedListing.user_id == user_id, ViewedListing.listing_id.not_in(newest)
            )
        )

    async def recent(self, user_id: UUID, limit: int) -> list[tuple[Listing, datetime]]:
        """Недавно смотренные квартиры (новые сверху), удалённые не показываем."""
        query = (
            select(Listing, ViewedListing.viewed_at)
            .join(ViewedListing, ViewedListing.listing_id == Listing.id)
            .where(ViewedListing.user_id == user_id, Listing.is_deleted.is_(False))
            .order_by(ViewedListing.viewed_at.desc())
            .limit(limit)
        )
        return [(listing, viewed) for listing, viewed in await self._session.execute(query)]

    async def clear(self, user_id: UUID) -> None:
        await self._session.execute(delete(ViewedListing).where(ViewedListing.user_id == user_id))
