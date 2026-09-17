from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bina.application.repositories.listings import IListingsRepository
from src.bina.infrastructure.db.models import Listing, ListingStatus

if TYPE_CHECKING:
    from collections.abc import Sequence


class ListingsRepository(IListingsRepository):
    """Реализация репозитория объявлений."""
    
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
    
    async def get_active_listings_by_district(
        self,
        district_id: UUID,
        limit: int,
    ) -> list[Listing]:
        """Получить активные объявления по району."""
        query = (
            select(Listing)
            .where(
                Listing.district_id == district_id,
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
            )
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )
        
        result = await self._session.execute(query)
        listings: Sequence[Listing] = result.scalars().all()
        return list(listings)