from unittest.mock import AsyncMock, patch

import pytest

from bina.infrastructure.scrapers.base_scraper import BaseWebsiteScraper


class _TestScraper(BaseWebsiteScraper):
    """Тестовый парсер для базового класса."""
    
    async def scrape_listings(self, limit: int):
        """Заглушка метода scrape_listings."""
        return []


@pytest.mark.asyncio
async def test_base_scraper_fetch_page():
    """Тест метода _fetch_page базового парсера."""
    # Создаем мок HTTP клиента
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = "<html>test</html>"
        mock_client.get.return_value = mock_response
        
        # Создаем парсер
        scraper = _TestScraper("https://example.com", delay_seconds=0)
        
        # Вызываем метод
        result = await scraper._fetch_page("https://example.com/test")
        
        # Проверяем результат
        assert result == "<html>test</html>"
        mock_client.get.assert_called_once_with(
            "https://example.com/test", 
            headers={"User-Agent": mock_client.get.call_args[1]["headers"]["User-Agent"]}
        )


@pytest.mark.asyncio
async def test_base_scraper_close():
    """Тест метода close базового парсера."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        scraper = _TestScraper("https://example.com")
        await scraper.close()
        
        mock_client.aclose.assert_called_once()