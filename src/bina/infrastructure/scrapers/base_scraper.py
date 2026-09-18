import asyncio
import random
from abc import ABC, abstractmethod

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.bina.application.ports.scraper import BaseScraper, RawListing

logger = structlog.get_logger(__name__)


class BaseWebsiteScraper(BaseScraper, ABC):
    """Базовый класс для парсера веб-сайтов."""

    def __init__(
        self,
        base_url: str,
        delay_seconds: int = 2,
        user_agents: list[str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.delay_seconds = delay_seconds
        self.user_agents = user_agents or [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ]
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Ленивый инициализатор HTTP клиента."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Закрывает HTTP клиент."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def _fetch_page(self, url: str) -> str:
        """Получает HTML страницу с rate limiting."""
        # Выбираем случайный User-Agent
        headers = {"User-Agent": random.choice(self.user_agents)}

        logger.debug("Fetching page", url=url)
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()

        # Rate limiting
        await asyncio.sleep(self.delay_seconds)

        return response.text

    @abstractmethod
    async def scrape_listings(self, limit: int) -> list[RawListing]:
        """Парсит объявления из источника."""
        pass
