from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.ss_scraper import SSScraper


@pytest.fixture
def ss_scraper() -> SSScraper:
    """Фикстура для SS парсера (только страницы списка)."""
    return SSScraper(delay_seconds=0, fetch_details=False)


@pytest.mark.asyncio
async def test_ss_parse_listings(ss_scraper: SSScraper) -> None:
    """Тест парсинга объявлений с SS."""
    # Читаем тестовые данные
    html = Path("tests/unit/infrastructure/scrapers/test_data/ss_test.html").read_text(
        encoding="utf-8"
    )

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
async def test_ss_scrape_listings_pages_and_limit(ss_scraper: SSScraper, tmp_path: Path) -> None:
    """Лимит, остановка на пустой странице, сохранение HTML первой страницы."""
    html = _list_html()
    second = html.replace("12345", "22222").replace("67890", "33333")
    fake = FakePages({1: html, 2: second})
    setattr(ss_scraper, "_fetch_page", fake)
    ss_scraper.dump_dir = tmp_path

    listings = await ss_scraper.scrape_listings(10)

    assert [item.source_id for item in listings] == ["12345", "67890", "22222", "33333"]
    assert len(fake.requested) == 3  # третья страница пустая
    assert fake.requested[0].startswith("https://home.ss.ge/ru/")
    assert (tmp_path / "ss_list.html").read_text(encoding="utf-8") == html

    setattr(ss_scraper, "_fetch_page", FakePages({1: html, 2: second}))
    assert len(await ss_scraper.scrape_listings(3)) == 3


@pytest.mark.asyncio
async def test_ss_stops_when_page_number_is_ignored(ss_scraper: SSScraper) -> None:
    """Сайт отдаёт одну и ту же страницу на любой номер — не зацикливаемся."""
    fake = FakePages({}, default=_list_html())
    setattr(ss_scraper, "_fetch_page", fake)

    listings = await ss_scraper.scrape_listings(100)

    assert [item.source_id for item in listings] == ["12345", "67890"]
    assert len(fake.requested) == 2


@pytest.mark.asyncio
async def test_ss_skips_failed_pages(ss_scraper: SSScraper) -> None:
    html = _list_html()
    error = httpx.ConnectError("boom")
    fake = FakePages({1: error, 2: html})
    setattr(ss_scraper, "_fetch_page", fake)
    assert len(await ss_scraper.scrape_listings(10)) == 2

    fake = FakePages({1: error, 2: error, 3: error, 4: html})
    setattr(ss_scraper, "_fetch_page", fake)
    assert await ss_scraper.scrape_listings(10) == []
    assert len(fake.requested) == 3


NEXT_LIST_HTML = Path("tests/unit/infrastructure/scrapers/test_data/ss_next_list.html").read_text(
    encoding="utf-8"
)


def test_parse_next_data_page(ss_scraper: SSScraper) -> None:
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


def test_other_cities_do_not_stop_paging(ss_scraper: SSScraper) -> None:
    """Страница только с Батуми — не конец выдачи; без фильтра города берутся все."""
    ids, listings = ss_scraper._parse_page(NEXT_LIST_HTML)
    assert ids == {"36583130", "36627728", "36773935"}
    assert len(listings) == 2

    ss_scraper.city_id = None
    assert len(ss_scraper._parse_listings(NEXT_LIST_HTML)) == 3


def test_rooms_fallback_to_bedrooms() -> None:
    from bina.infrastructure.scrapers.ss_scraper import _rooms

    assert _rooms("Аренда 3-комнатная Квартира", 2) == 3
    assert _rooms("Аренда Квартира", 2) == 3
    assert _rooms("Аренда Квартира", None) == 1


DETAIL_HTML = Path("tests/unit/infrastructure/scrapers/test_data/ss_detail.html")


@pytest.mark.asyncio
async def test_ss_detail_page_adds_everything() -> None:
    """Страница объявления (реальная, сокращённая): полное описание, удобства, этажи."""
    scraper = SSScraper(delay_seconds=0)
    card = RawListing(
        source_id="36583130",
        source_name="ss",
        title="Аренда 2-комнатная Квартира. Сололаки",
        description="Сдается комфортная… (обрезано)",
        price=2610,
        currency="GEL",
        rooms=2,
        area=68,
        district="Сололаки",
        url="https://home.ss.ge/ru/detail",
    )
    requested: list[str] = []

    async def fetch(url: str) -> str:
        requested.append(url)
        return DETAIL_HTML.read_text(encoding="utf-8")

    setattr(scraper, "_fetch_page", fetch)
    listing = await scraper.with_details(card)

    assert requested == ["https://home.ss.ge/ru/detail"]
    assert listing.has_details
    assert listing.description.startswith("Сдается комфортная, отремонтированная квартира")
    assert len(listing.description) > 500
    assert set(listing.descriptions) == {"ka", "en"}
    assert listing.descriptions["ka"].startswith("ქირავდება")
    assert listing.phone == "595000000"
    assert (listing.owner_name, listing.owner_type) == ("სალომე", "owner")
    assert (listing.floor, listing.total_floors, listing.bedrooms, listing.bathrooms) == (
        4,
        4,
        1,
        1,
    )
    assert listing.condition == "newly_renovated"
    assert listing.features == [
        "furniture",
        "air_conditioning",
        "heating",
        "hot_water",
        "washing_machine",
        "fridge",
        "tv",
        "internet",
        "gas",
        "storage",
    ]
    assert listing.address == "ул. Мачабели 6"
    assert listing.latitude == pytest.approx(41.6917456)
    assert listing.updated_at == datetime(2026, 9, 28, 6, 4, 32, 440921, tzinfo=UTC)
    assert listing.photos[0].endswith(".jpg") and "_Thumb" not in listing.photos[0]


@pytest.mark.asyncio
async def test_ss_detail_page_failure_keeps_card() -> None:
    scraper = SSScraper(delay_seconds=0)
    card = RawListing("1", "ss", "t", "d", 1000, "GEL", 2, 50, "Ваке", "https://x/1")

    async def fail(url: str) -> str:
        raise httpx.ConnectError("down")

    setattr(scraper, "_fetch_page", fail)
    assert await scraper.with_details(card) is card

    async def junk(url: str) -> str:
        return "<html>no data</html>"

    setattr(scraper, "_fetch_page", junk)
    assert (await scraper.with_details(card)).has_details is False
