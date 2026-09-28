import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.embeddings import EmbeddingsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.llm.llm_factory import LLMFactory

logger = structlog.get_logger(__name__)


class ScrapedListingsRepository:
    """Сохранение спарсенных объявлений в БД (и, по желанию, embeddings).

    Каждое объявление сохраняется в отдельном savepoint: ошибка одного не
    откатывает остальные. Коммит делает вызывающий код.
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_factory: LLMFactory | None = None,
    ) -> None:
        self.session = session
        self.listing_repository = ListingsRepository(session)
        self.llm_factory = llm_factory

    async def save_listings(self, listings: list[RawListing]) -> int:
        """Сохраняет объявления; возвращает количество успешно сохранённых."""
        saved_count = 0
        for raw_listing in listings:
            try:
                async with self.session.begin_nested():
                    listing = await self.listing_repository.create_or_update_from_raw(raw_listing)
            except (SQLAlchemyError, ValueError) as exc:
                logger.error(
                    "Error saving listing",
                    source_id=raw_listing.source_id,
                    source_name=raw_listing.source_name,
                    error=str(exc),
                )
                continue
            saved_count += 1
            if self.llm_factory is not None:
                await self._create_embedding(listing)

        logger.info("Saved listings to DB", count=saved_count)
        return saved_count

    async def _create_embedding(self, listing: Listing) -> None:
        """Создаёт embedding объявления; ошибки не прерывают сохранение."""
        assert self.llm_factory is not None
        title = listing.title_ru or listing.title_ka
        text = f"{title} {listing.description_ru or listing.description_ka}"
        try:
            provider = self.llm_factory.create_embeddings_provider()
            embedding = await provider.generate_embedding(text)
            async with self.session.begin_nested():
                await EmbeddingsRepository(self.session).save_embedding(listing.id, embedding)
        except Exception as exc:  # noqa: BLE001 - внешний API: любая ошибка не критична
            logger.warning("Failed to create embedding", listing_id=listing.id, error=str(exc))
