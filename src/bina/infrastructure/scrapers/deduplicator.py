from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import structlog

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import Listing as ListingModel
from bina.infrastructure.db.models import ListingStatus
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
                logger.debug(
                    "New listing found",
                    source_id=listing.source_id,
                    source_name=listing.source_name,
                )
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
            elif existing_listing.status != ListingStatus.ACTIVE:
                # Снятое раньше объявление снова на сайте
                unique_listings.append(listing)
            elif details_changed(existing_listing, listing):
                # Появились подробности со страницы объявления или сайт обновил объявление
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


def details_changed(existing: ListingModel, listing: RawListing) -> bool:
    """Нужно ли пересохранить объявление, хотя цена та же (TASK-018).

    Да, если впервые загружена страница объявления или дата обновления на сайте
    изменилась (владелец поправил текст, фото, удобства).
    """
    if listing.has_details and existing.details_fetched_at is None:
        return True
    return listing.updated_at is not None and listing.updated_at != existing.source_updated_at


@dataclass(frozen=True, slots=True)
class KnownListing:
    """То, что база уже знает об объявлении (для решения, открывать ли его страницу)."""

    price: Decimal
    status: ListingStatus
    details_fetched_at: datetime | None
    source_updated_at: datetime | None


def needs_details(known: KnownListing | None, card: RawListing, price: float) -> bool:
    """Открывать ли страницу объявления из списка.

    Да, если объявление новое, без подробностей, было снято, изменилась цена
    (``price`` — цена карточки в валюте базы) или дата обновления на сайте.
    Иначе оно не менялось: запрос к сайту не нужен.
    """
    if known is None or known.details_fetched_at is None:
        return True
    if known.status != ListingStatus.ACTIVE or known.price != Decimal(str(price)):
        return True
    return card.updated_at is not None and card.updated_at != known.source_updated_at
