from unittest.mock import AsyncMock
from decimal import Decimal

import pytest
from uuid import UUID

from bina.application.dtos.listing_dto import TranslatedListingDTO
from bina.application.use_cases.translate_listing import TranslateListingUseCase
from bina.infrastructure.db.models import Listing


@pytest.mark.asyncio
async def test_translate_listing_use_case_with_mock_llm() -> None:
    """Тест use-case перевода с mock LLM."""
    # Создаем моки зависимостей
    llm_provider = AsyncMock()
    listing_repository = AsyncMock()
    semantic_cache = AsyncMock()
    
    # Настройка мока репозитория
    listing_id = UUID("12345678-1234-5678-1234-567812345678")
    listing = Listing(
        id=listing_id,
        source_id="test-source",
        source_name="test-source",
        title_ru="Original RU",
        title_ka="სახელი ქართულად",
        description_ru="Original description RU",
        description_ka="აღწერა ქართულად",
        price=Decimal("1000"),
        currency="GEL",
        district_id=UUID("12345678-1234-5678-1234-567812345679"),
        rooms=2,
        area=Decimal("50.0"),
    )
    listing_repository.get_by_id.return_value = listing
    
    # Настройка мока кэша (пустой кэш)
    semantic_cache.get.return_value = None
    
    # Настройка мока LLM
    llm_provider.complete_structured.return_value = {
        "title_ru": "Переведенный заголовок",
        "description_ru": "Переведенное описание",
    }
    
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
    assert result.title_ru == "Переведенный заголовок"
    assert result.description_ru == "Переведенное описание"
    assert result.price == 1000.0
    assert result.rooms == 2
    assert result.area == 50.0
    
    # Проверяем вызовы
    listing_repository.get_by_id.assert_called_once_with(listing_id)
    semantic_cache.get.assert_called_once()
    llm_provider.complete_structured.assert_called_once()
    semantic_cache.set.assert_called_once()
    listing_repository.save_translation.assert_called_once_with(
        listing_id,
        title_ru="Переведенный заголовок",
        description_ru="Переведенное описание",
    )


@pytest.mark.asyncio
async def test_translate_listing_use_case_with_cached_result() -> None:
    """Тест use-case перевода с использованием кэша."""
    # Создаем моки зависимостей
    llm_provider = AsyncMock()
    listing_repository = AsyncMock()
    semantic_cache = AsyncMock()
    
    # Настройка мока репозитория
    listing_id = UUID("12345678-1234-5678-1234-567812345678")
    listing = Listing(
        id=listing_id,
        source_id="test-source",
        source_name="test-source",
        title_ru="Original RU",
        title_ka="სახელი ქართულად",
        description_ru="Original description RU",
        description_ka="აღწერა ქართულად",
        price=Decimal("1000"),
        currency="GEL",
        district_id=UUID("12345678-1234-5678-1234-567812345679"),
        rooms=2,
        area=Decimal("50.0"),
    )
    listing_repository.get_by_id.return_value = listing
    
    # Настройка мока кэша (есть результат в кэше)
    cached_result = {
        "title_ru": "Кэшированный заголовок",
        "description_ru": "Кэшированное описание",
    }
    semantic_cache.get.return_value = cached_result
    
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
    assert result.title_ru == "Кэшированный заголовок"
    assert result.description_ru == "Кэшированное описание"
    assert result.price == 1000.0
    assert result.rooms == 2
    assert result.area == 50.0
    
    # Проверяем вызовы (LLM не должен быть вызван)
    listing_repository.get_by_id.assert_called_once_with(listing_id)
    semantic_cache.get.assert_called_once()
    llm_provider.complete_structured.assert_not_called()
    semantic_cache.set.assert_not_called()
    listing_repository.save_translation.assert_called_once_with(
        listing_id,
        title_ru="Кэшированный заголовок",
        description_ru="Кэшированное описание",
    )


@pytest.mark.asyncio
async def test_translate_listing_use_case_listing_not_found() -> None:
    """Тест use-case перевода когда объявление не найдено."""
    # Создаем моки зависимостей
    llm_provider = AsyncMock()
    listing_repository = AsyncMock()
    semantic_cache = AsyncMock()
    
    # Настройка мока репозитория (объявление не найдено)
    listing_id = UUID("12345678-1234-5678-1234-567812345678")
    listing_repository.get_by_id.return_value = None
    
    # Создаем use-case
    use_case = TranslateListingUseCase(
        llm_provider=llm_provider,
        listing_repository=listing_repository,
        semantic_cache=semantic_cache,
    )
    
    # Проверяем, что выбрасывается исключение
    with pytest.raises(ValueError, match=f"Listing with id {listing_id} not found"):
        await use_case.execute(listing_id)