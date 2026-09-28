from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.ports.scraper import RawListing
from bina.application.ports.translator import LANGUAGES, ListingText
from bina.application.repositories.listings import IListingsRepository
from bina.infrastructure.db.models import District, Listing, ListingStatus

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
    
    async def search(
        self,
        filters: ListingSearchFilters,
        limit: int,
        offset: int = 0,
    ) -> list[Listing]:
        """Найти активные объявления по фильтрам (новые сверху)."""
        query = (
            select(Listing)
            .where(*self._search_conditions(filters))
            .order_by(Listing.created_at.desc(), Listing.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: ListingSearchFilters) -> int:
        """Количество активных объявлений, подходящих под фильтры."""
        query = (
            select(func.count())
            .select_from(Listing)
            .where(*self._search_conditions(filters))
        )
        result = await self._session.execute(query)
        return int(result.scalar_one())

    @staticmethod
    def _search_conditions(filters: ListingSearchFilters) -> list[ColumnElement[bool]]:
        """Собирает условия WHERE для поиска по фильтрам."""
        conditions: list[ColumnElement[bool]] = [
            Listing.status == ListingStatus.ACTIVE,
            Listing.is_deleted.is_(False),
        ]
        if filters.district_id is not None:
            conditions.append(Listing.district_id == filters.district_id)
        if filters.price_min is not None:
            conditions.append(Listing.price >= filters.price_min)
        if filters.price_max is not None:
            conditions.append(Listing.price <= filters.price_max)
        if filters.rooms_min is not None:
            conditions.append(Listing.rooms >= filters.rooms_min)
        if filters.rooms_max is not None:
            conditions.append(Listing.rooms <= filters.rooms_max)
        return conditions

    async def create_or_update_from_raw(
        self,
        raw_listing: RawListing,
    ) -> Listing:
        """Создать или обновить объявление из RawListing.

        Текст попадает в ``title_ru``/``description_ru`` или ``*_ka`` по
        ``raw_listing.language``; перевод на другой язык при обновлении сохраняется.
        """
        district = await self._get_or_create_district(raw_listing.district)
        suffix = "ka" if raw_listing.language == "ka" else "ru"
        values: dict[str, object] = {
            f"title_{suffix}": raw_listing.title,
            f"description_{suffix}": raw_listing.description,
            "price": Decimal(str(raw_listing.price)),
            "currency": raw_listing.currency,
            "rooms": raw_listing.rooms,
            "area": Decimal(str(raw_listing.area)),
            "district_id": district.id,
            "images": list(raw_listing.photos),
            "url": raw_listing.url or None,
            "phone": raw_listing.phone,
            "owner_name": raw_listing.owner_name,
            "status": ListingStatus.ACTIVE,
            "is_deleted": False,
        }

        listing = await self.find_by_source(raw_listing.source_id, raw_listing.source_name)
        if listing is not None:
            values.update(
                stale_translation_resets(
                    listing, suffix, raw_listing.title, raw_listing.description
                )
            )
        if listing is None:
            listing = Listing(
                source_id=raw_listing.source_id,
                source_name=raw_listing.source_name,
                # Второй язык заполнит перевод (TranslateListingUseCase)
                title_ru="",
                title_ka="",
                description_ru="",
                description_ka="",
                title_en="",
                description_en="",
            )
            self._session.add(listing)
        for key, value in values.items():
            setattr(listing, key, value)

        await self._session.flush()  # ID нужен для embeddings
        return listing

    async def list_untranslated(self, limit: int) -> list[Listing]:
        """Активные объявления с пустым заголовком хотя бы на одном языке (новые сверху)."""
        query = (
            select(Listing)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                or_(*(getattr(Listing, f"title_{language}") == "" for language in LANGUAGES)),
            )
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def save_texts(self, listing_id: UUID, texts: dict[str, ListingText]) -> None:
        """Записать заголовок и описание для каждого языка из ``texts``."""
        values: dict[str, str] = {}
        for language, text in texts.items():
            if language in LANGUAGES:
                values[f"title_{language}"] = text.title
                values[f"description_{language}"] = text.description
        if values:
            await self._session.execute(
                update(Listing).where(Listing.id == listing_id).values(**values)
            )

    async def _get_or_create_district(self, district_name: str) -> District:
        """Получает или создает район."""
        # В реальной реализации нужно добавить репозиторий районов
        # Пока вернем первый найденный район или создадим заглушку
        from bina.infrastructure.db.repositories.districts import DistrictsRepository
        
        districts_repo = DistrictsRepository(self._session)
        district = await districts_repo.get_by_name(district_name)
        if district is None:
            district = await districts_repo.create_district(district_name)
        return district

def stale_translation_resets(
    listing: Listing, language: str, title: str, description: str
) -> dict[str, str]:
    """Пустые поля других языков, если исходный текст объявления изменился.

    Перевод старого текста больше не верен: после сброса его заново сделает
    ``TranslateListingsUseCase``. Если текст тот же, переводы остаются.
    """
    old = (
        getattr(listing, f"title_{language}", "") or "",
        getattr(listing, f"description_{language}", "") or "",
    )
    if old == (title, description):
        return {}
    resets: dict[str, str] = {}
    for other in LANGUAGES:
        if other != language:
            resets[f"title_{other}"] = ""
            resets[f"description_{other}"] = ""
    return resets
