from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.bina.application.ports.scraper import RawListing
from src.bina.application.repositories.listings import IListingsRepository
from src.bina.infrastructure.db.models import District, Listing, ListingStatus

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
    
    async def get_by_id(self, listing_id: UUID) -> Listing | None:
        """Получить объявление по ID."""
        query = select(Listing).where(Listing.id == listing_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def find_by_source(
        self,
        source_id: str,
        source_name: str,
    ) -> Listing | None:
        """Найти объявление по source_id и source_name."""
        query = select(Listing).where(
            Listing.source_id == source_id,
            Listing.source_name == source_name,
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def save_translation(
        self,
        listing_id: UUID,
        title_ru: str,
        description_ru: str,
    ) -> None:
        """Сохранить перевод объявления."""
        query = (
            update(Listing)
            .where(Listing.id == listing_id)
            .values(title_ru=title_ru, description_ru=description_ru)
        )
        await self._session.execute(query)
    
    async def create_or_update_from_raw(
        self,
        raw_listing: RawListing,
    ) -> Listing:
        """Создать или обновить объявление из RawListing."""
        # Найдем существующее объявление
        existing_listing = await self.find_by_source(
            raw_listing.source_id,
            raw_listing.source_name,
        )
        
        if existing_listing is not None:
            # Обновляем существующее объявление
            existing_listing.price = raw_listing.price
            existing_listing.currency = raw_listing.currency
            existing_listing.rooms = raw_listing.rooms
            existing_listing.area = raw_listing.area
            existing_listing.title = raw_listing.title
            existing_listing.description = raw_listing.description
            existing_listing.url = raw_listing.url
            existing_listing.photos = raw_listing.photos
            existing_listing.status = ListingStatus.ACTIVE
            
            # Обновляем район
            district = await self._get_or_create_district(raw_listing.district)
            existing_listing.district_id = district.id
            
            return existing_listing
        else:
            # Создаем новое объявление
            district = await self._get_or_create_district(raw_listing.district)
            
            new_listing = Listing(
                source_id=raw_listing.source_id,
                source_name=raw_listing.source_name,
                title=raw_listing.title,
                description=raw_listing.description,
                price=raw_listing.price,
                currency=raw_listing.currency,
                rooms=raw_listing.rooms,
                area=raw_listing.area,
                district_id=district.id,
                url=raw_listing.url,
                photos=raw_listing.photos,
                status=ListingStatus.ACTIVE,
            )
            
            self._session.add(new_listing)
            await self._session.flush()  # Получаем ID для последующей работы с embeddings
            return new_listing
    
    async def _get_or_create_district(self, district_name: str) -> District:
        """Получает или создает район."""
        # В реальной реализации нужно добавить репозиторий районов
        # Пока вернем первый найденный район или создадим заглушку
        from src.bina.infrastructure.db.repositories.districts import DistrictsRepository
        
        districts_repo = DistrictsRepository(self._session)
        district = await districts_repo.get_by_name(district_name)
        if district is None:
            district = await districts_repo.create_district(district_name)
        return district