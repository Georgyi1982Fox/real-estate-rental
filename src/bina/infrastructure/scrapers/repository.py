
import structlog

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.llm.llm_factory import LLMFactory

logger = structlog.get_logger(__name__)


class ScrapedListingsRepository:
    """Репозиторий для сохранения спарсенных объявлений в БД."""

    def __init__(
        self,
        listing_repository: ListingsRepository,
        llm_factory: LLMFactory,
    ) -> None:
        self.listing_repository = listing_repository
        self.llm_factory = llm_factory

    async def save_listings(self, listings: list[RawListing]) -> int:
        """Сохраняет объявления в БД и создает embeddings."""
        saved_count = 0

        for raw_listing in listings:
            try:
                # Создаем или обновляем объявление
                listing_model = await self.listing_repository.create_or_update_from_raw(raw_listing)

                # Создаем embedding для объявления
                await self._create_embedding(listing_model)

                saved_count += 1
                logger.debug("Saved listing", source_id=raw_listing.source_id, source_name=raw_listing.source_name)

            except Exception as e:
                logger.error(
                    "Error saving listing",
                    source_id=raw_listing.source_id,
                    source_name=raw_listing.source_name,
                    error=str(e),
                )
                continue

        logger.info("Saved listings to DB", count=saved_count)
        return saved_count

    async def _create_embedding(self, listing: "Listing") -> None:  # type: ignore[name-defined]
        """Создает embedding для объявления."""
        try:
            # Получаем текст для embedding
            text = f"{listing.title} {listing.description}"

            # Получаем провайдер embeddings
            embeddings_provider = self.llm_factory.create_embeddings_provider()

            # Генерируем embedding
            embedding = await embeddings_provider.generate_embedding(text)

            # Сохраняем embedding в БД
            from bina.infrastructure.db.repositories.embeddings import EmbeddingsRepository

            embeddings_repo = EmbeddingsRepository(self.listing_repository._session)
            await embeddings_repo.save_embedding(listing.id, embedding)

            logger.debug("Created embedding for listing", listing_id=listing.id)

        except Exception as e:
            logger.warning("Failed to create embedding", listing_id=listing.id, error=str(e))
