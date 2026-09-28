from pathlib import Path

import httpx
import pytest

from bina.infrastructure.scrapers.ss_scraper import SSScraper


@pytest.fixture
def ss_scraper():
    """Фикстура для SS парсера."""
    return SSScraper(delay_seconds=0)


@pytest.mark.asyncio
async def test_ss_parse_listings(ss_scraper):
    """Тест парсинга объявлений с SS."""
    # Читаем тестовые данные
    with open("tests/unit/infrastructure/scrapers/test_data/ss_test.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    # Парсим объявления
    listings = ss_scraper._parse_listings(html)
    
    # Проверяем результат
    assert len(listings) == 2
    
    # Проверяем первое объявление
    listing1 = listings[0]
    assert listing1.source_id == "12345"
    assert listing1.source_name == "ss"
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


class FakePages:
    """Подменяет ``_fetch_page``: номер страницы → HTML или исключение."""

    def __init__(self, pages: dict[int, str | Exception], default: str = "<html></html>") -> None:
        self.pages = pages
        self.default = default
        self.requested: list[str] = []

    async def __call__(self, url: str) -> str:
        self.requested.append(url)
        page = int(url.rsplit("page=", 1)[1])
        value = self.pages.get(page, self.default)
        if isinstance(value, Exception):
            raise value
        return value


def _list_html() -> str:
    return Path("tests/unit/infrastructure/scrapers/test_data/ss_test.html").read_text(
        encoding="utf-8"
    )


@pytest.mark.asyncio
async def test_ss_scrape_listings_pages_and_limit(ss_scraper, tmp_path):
    """Лимит, остановка на пустой странице, сохранение HTML первой страницы."""
    html = _list_html()
    second = html.replace("12345", "22222").replace("67890", "33333")
    fake = FakePages({1: html, 2: second})
    ss_scraper._fetch_page = fake
    ss_scraper.dump_dir = tmp_path

    listings = await ss_scraper.scrape_listings(10)

    assert [item.source_id for item in listings] == ["12345", "67890", "22222", "33333"]
    assert len(fake.requested) == 3  # третья страница пустая
    assert fake.requested[0].startswith("https://home.ss.ge/ru/")
    assert (tmp_path / "ss_list.html").read_text(encoding="utf-8") == html

    ss_scraper._fetch_page = FakePages({1: html, 2: second})
    assert len(await ss_scraper.scrape_listings(3)) == 3


@pytest.mark.asyncio
async def test_ss_stops_when_page_number_is_ignored(ss_scraper):
    """Сайт отдаёт одну и ту же страницу на любой номер — не зацикливаемся."""
    fake = FakePages({}, default=_list_html())
    ss_scraper._fetch_page = fake

    listings = await ss_scraper.scrape_listings(100)

    assert [item.source_id for item in listings] == ["12345", "67890"]
    assert len(fake.requested) == 2


@pytest.mark.asyncio
async def test_ss_skips_failed_pages(ss_scraper):
    html = _list_html()
    error = httpx.ConnectError("boom")
    fake = FakePages({1: error, 2: html})
    ss_scraper._fetch_page = fake
    assert len(await ss_scraper.scrape_listings(10)) == 2

    fake = FakePages({1: error, 2: error, 3: error, 4: html})
    ss_scraper._fetch_page = fake
    assert await ss_scraper.scrape_listings(10) == []
    assert len(fake.requested) == 3
