
import structlog

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import Listing as ListingModel
from bina.infrastructure.db.repositories.listings import ListingsRepository

logger = structlog.get_logger(__name__)


class ListingDeduplicator:
    """Дедупликатор объявлений."""

    def __init__(self, listing_repository: ListingsRepository) -> None:
        self.listing_repository = listing_repository

    async def deduplicate(
        self,
        listings: list[RawListing],
    ) -> list[RawListing]:
        """Удаляет дубликаты и обновляет изменившиеся объявления."""
        unique_listings: list[RawListing] = []

        for listing in listings:
            # Проверяем существующее объявление по source_id + source_name
            existing_listing = await self._find_existing_listing(listing)

            if existing_listing is None:
                # Новое объявление
                unique_listings.append(listing)
                logger.debug("New listing found", source_id=listing.source_id, source_name=listing.source_name)
            elif existing_listing.price != listing.price:
                # Цена изменилась - обновляем
                logger.info(
                    "Price changed for existing listing",
                    source_id=listing.source_id,
                    source_name=listing.source_name,
                    old_price=existing_listing.price,
                    new_price=listing.price,
                )
                unique_listings.append(listing)
            else:
                # Дубликат с той же ценой - пропускаем
                logger.debug(
                    "Duplicate listing skipped",
                    source_id=listing.source_id,
                    source_name=listing.source_name,
                )

        logger.info("Deduplication completed", total=len(listings), unique=len(unique_listings))
        return unique_listings

    async def _find_existing_listing(self, listing: RawListing) -> ListingModel | None:
        """Находит существующее объявление по source_id + source_name."""
        return await self.listing_repository.find_by_source(
            listing.source_id,
            listing.source_name,
        )
