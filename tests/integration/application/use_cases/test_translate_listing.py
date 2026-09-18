import os
from unittest.mock import AsyncMock

import pytest
from uuid import UUID

from src.bina.application.dtos.listing_dto import TranslatedListingDTO
from src.bina.application.use_cases.translate_listing import TranslateListingUseCase
from src.bina.infrastructure.db.models import Listing
from src.bina.infrastructure.llm.llm_factory import LLMFactory
from src.bina.infrastructure.llm.semantic_cache import SemanticCache


# Пропускаем тест, если нет API ключа
pytestmark = pytest.mark.skipif(
    not os.getenv("LLM_API_KEY"),
    reason="LLM_API_KEY environment variable not set",
)


@pytest.mark.asyncio
async def test_translate_listing_use_case_with_real_llm() -> None:
    """Интеграционный тест use-case перевода с реальным LLM через AITUNNEL."""
    # Создаем зависимости
    llm_provider = LLMFactory.create_provider()
    listing_repository = AsyncMock()
    semantic_cache = SemanticCache(redis_url="redis://localhost:6379/0", ttl_hours=24)
    
    # Настройка мока репозитория
    listing_id = UUID("12345678-1234-5678-1234-567812345678")
    listing = Listing(
        id=listing_id,
        source_id="test-source",
        source_name="test-source",
        title_ru="Original RU",
        title_ka="სათაური ქართულად - საცხოვრებელი ბინა გუხტუში",
        description_ru="Original description RU",
        description_ka="აღწერა ქართულად - მშვენიერი ბინა გუხტუში, ახალი რემონტით, 2 ოთახიანი",
        price=1000,
        currency="GEL",
        district_id=UUID("12345678-1234-5678-1234-567812345679"),
        rooms=2,
        area=50.0,
    )
    listing_repository.get_by_id.return_value = listing
    listing_repository.save_translation = AsyncMock()
    
    # Создаем use-case
    use_case = TranslateListingUseCase(
        llm_provider=llm_provider,
        listing_repository=listing_repository,
        semantic_cache=semantic_cache,
    )
    
    # Выполняем перевод
    result = await use_case.execute(listing_id)
    
    # Проверяем результат
    assert isinstance(result, TranslatedListingDTO)
    assert result.id == listing_id
    assert isinstance(result.title_ru, str)
    assert isinstance(result.description_ru, str)
    assert len(result.title_ru) > 0
    assert len(result.description_ru) > 0
    assert result.price == 1000
    assert result.rooms == 2
    assert result.area == 50.0
    
    # Закрываем провайдера
    if hasattr(llm_provider, "close"):
        await llm_provider.close()