"""Базовый парсер: HTTP, повторы, пауза между запросами (без сети)."""

import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from tenacity import wait_none

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.base_scraper import BaseWebsiteScraper


class _TestScraper(BaseWebsiteScraper):
    """Минимальная реализация для проверки базового класса."""

    async def scrape_listings(self, limit: int) -> list[RawListing]:
        return []


def make_scraper(handler: httpx.MockTransport, delay: int = 0) -> _TestScraper:
    scraper = _TestScraper("https://example.com/", delay_seconds=delay, user_agents=["UA-test"])
    scraper._client = httpx.AsyncClient(transport=handler)
    return scraper


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """Без экспоненциального ожидания между повторами (иначе тест идёт секунды)."""
    monkeypatch.setattr(BaseWebsiteScraper._fetch_page.retry, "wait", wait_none())  # type: ignore[attr-defined]


async def test_fetch_page_returns_text_with_user_agent() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text="<html>test</html>")

    scraper = make_scraper(httpx.MockTransport(handler))

    assert await scraper._fetch_page("https://example.com/test") == "<html>test</html>"
    assert seen[0].headers["User-Agent"] == "UA-test"
    assert scraper.base_url == "https://example.com"
    await scraper.close()


async def test_fetch_page_retries_then_succeeds() -> None:
    responses = iter([httpx.Response(503), httpx.Response(500), httpx.Response(200, text="ok")])
    scraper = make_scraper(httpx.MockTransport(lambda request: next(responses)))

    assert await scraper._fetch_page("https://example.com/") == "ok"
    await scraper.close()


async def test_fetch_page_gives_up_after_three_attempts() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(500)

    scraper = make_scraper(httpx.MockTransport(handler))

    with pytest.raises(httpx.HTTPStatusError):
        await scraper._fetch_page("https://example.com/")
    assert len(calls) == 3
    await scraper.close()


async def test_rate_limit_sleeps_after_each_request(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)
    scraper = make_scraper(httpx.MockTransport(lambda request: httpx.Response(200)), delay=2)

    await scraper._fetch_page("https://example.com/")

    sleep.assert_awaited_once_with(2)
    await scraper.close()


async def test_close_releases_client() -> None:
    scraper = make_scraper(httpx.MockTransport(lambda request: httpx.Response(200)))
    client = scraper._client
    assert client is not None

    await scraper.close()

    assert client.is_closed
    assert scraper._client is None
