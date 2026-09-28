import asyncio
import random
from abc import ABC, abstractmethod

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from bina.application.ports.scraper import BaseScraper, RawListing
from bina.infrastructure.scrapers.settings import DEFAULT_USER_AGENTS

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
        self.user_agents = user_agents or list(DEFAULT_USER_AGENTS)
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
