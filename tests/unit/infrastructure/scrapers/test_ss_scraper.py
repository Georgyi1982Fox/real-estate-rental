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
    with open(
        "tests/unit/infrastructure/scrapers/test_data/ss_test.html", "r", encoding="utf-8"
    ) as f:
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


NEXT_LIST_HTML = Path("tests/unit/infrastructure/scrapers/test_data/ss_next_list.html").read_text(
    encoding="utf-8"
)


def test_parse_next_data_page(ss_scraper):
    """Настоящая страница home.ss.ge: JSON __NEXT_DATA__, только Тбилиси."""
    listings = ss_scraper._parse_listings(NEXT_LIST_HTML)

    assert [item.source_id for item in listings] == ["36583130", "36627728"]
    first = listings[0]
    assert first.source_name == "ss"
    assert first.title == "Аренда 2-комнатная Квартира. Сололаки"
    assert first.description.startswith("Сдается комфортная, отремонтированная квартира")
    assert (first.price, first.currency) == (2610.0, "GEL")
    assert (first.rooms, first.area) == (2, 68.0)
    assert first.district == "Сололаки"
    assert first.url == (
        "https://home.ss.ge/ru/%D0%BD%D0%B5%D0%B4%D0%B2%D0%B8%D0%B6%D0%B8%D0%BC%D0%BE%D1%81%D1%82%D1%8C/"
        "%D0%90%D1%80%D0%B5%D0%BD%D0%B4%D0%B0-2-%D0%BA%D0%BE%D0%BC%D0%BD%D0%B0%D1%82%D0%BD%D0%B0%D1%8F-"
        "%D0%9A%D0%B2%D0%B0%D1%80%D1%82%D0%B8%D1%80%D0%B0-%D0%A1%D0%BE%D0%BB%D0%BE%D0%BB%D0%B0%D0%BA%D0%B8-36583130"
    )
    # Главное фото первым (в фикстуре оно второе)
    assert len(first.photos) == 2
    assert first.photos[0].endswith("15_d33e55ba-47db-4e92-8fb3-4baa6239b437_Thumb.jpg")


def test_other_cities_do_not_stop_paging(ss_scraper):
    """Страница только с Батуми — не конец выдачи; без фильтра города берутся все."""
    ids, listings = ss_scraper._parse_page(NEXT_LIST_HTML)
    assert ids == {"36583130", "36627728", "36773935"}
    assert len(listings) == 2

    ss_scraper.city_id = None
    assert len(ss_scraper._parse_listings(NEXT_LIST_HTML)) == 3


def test_rooms_fallback_to_bedrooms():
    from bina.infrastructure.scrapers.ss_scraper import _rooms

    assert _rooms("Аренда 3-комнатная Квартира", 2) == 3
    assert _rooms("Аренда Квартира", 2) == 3
    assert _rooms("Аренда Квартира", None) == 1
