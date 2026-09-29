import asyncio
import random
from abc import ABC, abstractmethod

import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from bina.application.ports.scraper import BaseScraper, NeedsDetails, RawListing
from bina.infrastructure.scrapers.settings import DEFAULT_USER_AGENTS

logger = structlog.get_logger(__name__)

# Столько страниц списка подряд без новых и изменившихся объявлений — дальше
# идут старые, уже известные: парсинг останавливается
KNOWN_PAGES_TO_STOP = 2


class ListingGoneError(Exception):
    """Сайт увёл со страницы объявления на другую (объявления больше нет)."""

    def __init__(self, url: str, final_url: str) -> None:
        super().__init__(f"{url} redirected to {final_url}")
        self.url = url
        self.final_url = final_url


def _worth_retrying(exc: BaseException) -> bool:
    """Повторять сетевые сбои и 5xx; 4xx (404 — объявление снято) не изменится."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500 or exc.response.status_code == 429
    return isinstance(exc, httpx.HTTPError)


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
        self._detail_dumped = False

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
        retry=retry_if_exception(_worth_retrying),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def _fetch_page(self, url: str, expect: str | None = None) -> str:
        """Получает HTML страницу с rate limiting.

        ``expect``: ID объявления; если сайт перенаправил на адрес без него
        (например, на поиск), объявления больше нет — :class:`ListingGoneError`.
        """
        # Выбираем случайный User-Agent
        headers = {"User-Agent": random.choice(self.user_agents)}

        logger.debug("Fetching page", url=url)
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
        finally:
            # Rate limiting (и после ошибки: сайт не должен видеть очередь запросов)
            await asyncio.sleep(self.delay_seconds)

        final_url = str(response.url)
        if expect and response.history and expect not in final_url:
            raise ListingGoneError(url, final_url)
        return response.text

    async def with_details(self, card: RawListing, *, first: bool = False) -> RawListing:
        """Дополняет карточку данными страницы объявления (по умолчанию — ничего)."""
        return card

    async def _add_cards(
        self,
        cards: list[RawListing],
        listings: list[RawListing],
        limit: int,
        needs_details: NeedsDetails | None,
    ) -> int:
        """Добавляет карточки страницы списка в ``listings``.

        Страница объявления открывается только для новых и изменившихся (решает
        ``needs_details``). Возвращает, сколько таких было.
        """
        fresh = 0
        for card in cards[: limit - len(listings)]:
            if needs_details is None or await needs_details(card):
                card = await self.with_details(card, first=not self._detail_dumped)
                self._detail_dumped = True
                fresh += 1
            listings.append(card)
        return fresh

    @abstractmethod
    async def scrape_listings(
        self, limit: int, needs_details: NeedsDetails | None = None
    ) -> list[RawListing]:
        """Парсит объявления из источника."""
        pass
