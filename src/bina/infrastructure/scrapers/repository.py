import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.repositories.listings import ListingsRepository

logger = structlog.get_logger(__name__)


class ScrapedListingsRepository:
    """Сохранение спарсенных объявлений в БД (embeddings — отдельный шаг, TASK-012).

    Каждое объявление сохраняется в отдельном savepoint: ошибка одного не
    откатывает остальные. Коммит делает вызывающий код.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.listing_repository = ListingsRepository(session)

    async def save_listings(self, listings: list[RawListing]) -> int:
        """Сохраняет объявления; возвращает количество успешно сохранённых."""
        saved_count = 0
        for raw_listing in listings:
            try:
                async with self.session.begin_nested():
                    await self.listing_repository.create_or_update_from_raw(raw_listing)
            except (SQLAlchemyError, ValueError) as exc:
                logger.error(
                    "Error saving listing",
                    source_id=raw_listing.source_id,
                    source_name=raw_listing.source_name,
                    error=str(exc),
                )
                continue
            saved_count += 1

        logger.info("Saved listings to DB", count=saved_count)
        return saved_count
