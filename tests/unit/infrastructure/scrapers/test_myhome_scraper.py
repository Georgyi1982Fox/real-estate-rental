import pytest
from unittest.mock import AsyncMock, patch

from bina.infrastructure.scrapers.myhome_scraper import MyHomeScraper


@pytest.fixture
def myhome_scraper():
    """Фикстура для MyHome парсера."""
    return MyHomeScraper(delay_seconds=0)


@pytest.mark.asyncio
async def test_myhome_parse_listings(myhome_scraper):
    """Тест парсинга объявлений с MyHome."""
    # Читаем тестовые данные
    with open("tests/unit/infrastructure/scrapers/test_data/myhome_test.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    # Парсим объявления
    listings = myhome_scraper._parse_listings(html)
    
    # Проверяем результат
    assert len(listings) == 2
    
    # Проверяем первое объявление
    listing1 = listings[0]
    assert listing1.source_id == "12345"
    assert listing1.source_name == "myhome"
    assert "Test Apartment" in listing1.title
    assert "Beautiful apartment" in listing1.description
    assert listing1.price == 1000.0
    assert listing1.currency == "GEL"
    assert listing1.rooms == 2
    assert listing1.area == 50.0
    assert listing1.district == "ვაკე"
    assert "12345" in listing1.url
    assert len(listing1.photos) == 1
    
    # Проверяем второе объявление
    listing2 = listings[1]
    assert listing2.source_id == "67890"
    assert listing2.district == "საბურთალო"


@pytest.mark.asyncio
async def test_myhome_scrape_listings_integration(myhome_scraper):
    """Интеграционный тест парсинга с моком HTTP."""
    # Переопределяем метод для одной страницы
    original_scrape_listings = myhome_scraper.scrape_listings
    
    async def mock_scrape_listings(limit: int):
        # Мокаем HTML ответ
        with open("tests/unit/infrastructure/scrapers/test_data/myhome_test.html", "r", encoding="utf-8") as f:
            html = f.read()
        return myhome_scraper._parse_listings(html)[:limit]
    
    with patch.object(myhome_scraper, "scrape_listings", side_effect=mock_scrape_listings):
        # Вызываем метод
        listings = await original_scrape_listings(10)
        
        # Проверяем результат
        assert len(listings) == 2