from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from uuid import UUID

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import Listing, ListingStatus
from bina.infrastructure.scrapers.deduplicator import ListingDeduplicator


@pytest.fixture
def mock_listing_repository():
    """Мок репозитория объявлений."""
    return AsyncMock()


@pytest.fixture
def deduplicator(mock_listing_repository):
    """Фикстура для дедупликатора."""
    return ListingDeduplicator(mock_listing_repository)


@pytest.mark.asyncio
async def test_deduplicate_new_listings(deduplicator, mock_listing_repository):
    """Тест дедупликации новых объявлений."""
    # Настраиваем мок - не находим существующие объявления
    mock_listing_repository.find_by_source.return_value = None
    
    # Создаем тестовые объявления
    listings = [
        RawListing(
            source_id="123",
            source_name="myhome",
            title="Test 1",
            description="Desc 1",
            price=1000.0,
            currency="GEL",
            rooms=2,
            area=50.0,
            district="Vake",
            url="https://example.com/1",
            photos=[],
        ),
        RawListing(
            source_id="456",
            source_name="ss",
            title="Test 2",
            description="Desc 2",
            price=1500.0,
            currency="GEL",
            rooms=3,
            area=80.0,
            district="Saburtalo",
            url="https://example.com/2",
            photos=[],
        ),
    ]
    
    # Выполняем дедупликацию
    result = await deduplicator.deduplicate(listings)
    
    # Проверяем результат
    assert len(result) == 2
    mock_listing_repository.find_by_source.assert_any_call("123", "myhome")
    mock_listing_repository.find_by_source.assert_any_call("456", "ss")


@pytest.mark.asyncio
async def test_deduplicate_duplicate_same_price(deduplicator, mock_listing_repository):
    """Тест дедупликации дубликатов с той же ценой."""
    # Настраиваем мок - находим существующее объявление с той же ценой
    existing_listing = Listing(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        source_id="123",
        source_name="myhome",
        title_ru="Test",
        title_ka="Test",
        description_ru="Desc",
        description_ka="Desc",
        price=1000.0,
        currency="GEL",
        rooms=2,
        area_sqm=Decimal("50.0"),
        district_id=UUID("12345678-1234-5678-1234-567812345679"),
        url="https://example.com",
        photos=[],
        status=ListingStatus.ACTIVE,
    )
    mock_listing_repository.find_by_source.return_value = existing_listing
    
    # Создаем тестовое объявление (дубликат)
    listings = [
        RawListing(
            source_id="123",
            source_name="myhome",
            title="Test",
            description="Desc",
            price=1000.0,
            currency="GEL",
            rooms=2,
            area=50.0,
            district="Vake",
            url="https://example.com",
            photos=[],
        ),
    ]
    
    # Выполняем дедупликацию
    result = await deduplicator.deduplicate(listings)
    
    # Проверяем результат - дубликат должен быть проигнорирован
    assert len(result) == 0


@pytest.mark.asyncio
async def test_deduplicate_price_changed(deduplicator, mock_listing_repository):
    """Тест дедупликации при изменении цены."""
    # Настраиваем мок - находим существующее объявление с другой ценой
    existing_listing = Listing(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        source_id="123",
        source_name="myhome",
        title_ru="Test",
        title_ka="Test",
        description_ru="Desc",
        description_ka="Desc",
        price=1000.0,
        currency="GEL",
        rooms=2,
        area_sqm=Decimal("50.0"),
        district_id=UUID("12345678-1234-5678-1234-567812345679"),
        url="https://example.com",
        photos=[],
        status=ListingStatus.ACTIVE,
    )
    mock_listing_repository.find_by_source.return_value = existing_listing
    
    # Создаем тестовое объявление с измененной ценой
    listings = [
        RawListing(
            source_id="123",
            source_name="myhome",
            title="Test",
            description="Desc",
            price=1200.0,  # Цена изменилась
            currency="GEL",
            rooms=2,
            area=50.0,
            district="Vake",
            url="https://example.com",
            photos=[],
        ),
    ]
    
    # Выполняем дедупликацию
    result = await deduplicator.deduplicate(listings)
    
    # Проверяем результат - объявление должно быть включено для обновления
    assert len(result) == 1