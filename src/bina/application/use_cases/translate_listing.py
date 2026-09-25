from uuid import UUID

import structlog

from bina.application.dtos.listing_dto import TranslatedListingDTO
from bina.application.ports.llm_provider import LLMProvider
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.llm.prompts.translation_models import TranslationResponse
from bina.infrastructure.llm.semantic_cache import SemanticCache
from bina.infrastructure.llm.structured_output import (
    complete_structured_with_validation,
)

logger = structlog.get_logger(__name__)


class TranslateListingUseCase:
    """Use-case для перевода объявления с грузинского на русский."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        listing_repository: ListingsRepository,
        semantic_cache: SemanticCache,
    ) -> None:
        self.llm_provider = llm_provider
        self.listing_repository = listing_repository
        self.semantic_cache = semantic_cache

    async def execute(self, listing_id: UUID) -> TranslatedListingDTO:
        """Выполняет перевод объявления по ID."""
        logger.info("Translating listing", listing_id=listing_id)
        
        # Получаем объявление из БД
        listing = await self.listing_repository.get_by_id(listing_id)
        if not listing:
            raise ValueError(f"Listing with id {listing_id} not found")
        
        # Формируем текст для перевода
        georgian_text = f"Заголовок: {listing.title_ka}\nОписание: {listing.description_ka}"
        
        # Проверяем кэш
        cached_result = await self.semantic_cache.get(georgian_text)
        if cached_result:
            logger.debug("Using cached translation", listing_id=listing_id)
            result = cached_result
        else:
            # Выполняем перевод через LLM
            logger.debug("Translating with LLM", listing_id=listing_id)
            prompt = f"""Translate the following real estate listing from Georgian to Russian.

Title: {listing.title_ka}

Description: {listing.description_ka}

Return only the translated title and description in JSON format with keys "title_ru" and "description_ru". Do not include any other text."""
            
            translation_response = await complete_structured_with_validation(
                self.llm_provider,
                prompt,
                TranslationResponse,
            )
            result = translation_response.model_dump()
            
            # Сохраняем в кэш
            await self.semantic_cache.set(georgian_text, result)
            logger.debug("Translation completed and cached", listing_id=listing_id)
        
        # Создаем DTO
        dto = TranslatedListingDTO(
            id=listing.id,
            title_ru=result["title_ru"],
            description_ru=result["description_ru"],
            price=float(listing.price),
            rooms=listing.rooms,
            area=float(listing.area),
        )
        
        # Сохраняем перевод в БД
        await self.listing_repository.save_translation(
            listing_id,
            title_ru=dto.title_ru,
            description_ru=dto.description_ru,
        )
        logger.info("Translation saved to DB", listing_id=listing_id)
        
        return dto