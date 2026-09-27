"""Парсер MyHome.ge на HTML-фикстурах (без сети)."""

from pathlib import Path

import httpx
import pytest

from bina.infrastructure.scrapers.myhome_scraper import MyHomeScraper

DATA = Path(__file__).parent / "test_data"
LIST_HTML = (DATA / "myhome_test.html").read_text(encoding="utf-8")
DETAIL_HTML = (DATA / "myhome_detail_test.html").read_text(encoding="utf-8")
EMPTY_HTML = "<html><body>Ничего не найдено</body></html>"
BASE = "https://www.myhome.ge"


class FakePages:
    """Подменяет ``_fetch_page``: URL → HTML или исключение; записывает запросы."""

    def __init__(self, pages: dict[str, str | Exception], default: str = EMPTY_HTML) -> None:
        self.pages = pages
        self.default = default
        self.requested: list[str] = []

    async def __call__(self, url: str) -> str:
        self.requested.append(url)
        for key, value in self.pages.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        return self.default


def list_url(page: int) -> str:
    return f"&page={page}"


@pytest.fixture
def scraper() -> MyHomeScraper:
    return MyHomeScraper(delay_seconds=0)


def test_parse_list_page(scraper: MyHomeScraper) -> None:
    listings = scraper._parse_listings(LIST_HTML)

    assert [item.source_id for item in listings] == ["12345", "67890"]
    first = listings[0]
    assert first.source_name == "myhome"
    assert first.title == "Test Apartment in Vake"
    assert first.description == "Beautiful apartment in Vake district"
    assert (first.price, first.currency) == (1000.0, "GEL")
    assert (first.rooms, first.area) == (2, 50.0)
    assert first.district == "ვაკე"
    assert first.url == f"{BASE}/ru/12345/test-apartment"
    assert first.photos == ["https://example.com/photo1.jpg"]
    assert first.phone is None and first.owner_name is None


def test_parse_detail_page(scraper: MyHomeScraper) -> None:
    details = scraper._parse_detail(DETAIL_HTML)

    assert details["title"] == "Светлая квартира в Ваке"
    assert (details["price"], details["currency"]) == (1200.0, "GEL")
    assert (details["rooms"], details["area"]) == (3, 72.5)
    assert details["description"] == "Квартира после ремонта.\nРядом парк Ваке."
    assert details["photos"] == [
        "https://static.example.com/12345/1.jpg",
        f"{BASE}/uploads/12345/2.jpg",
    ]
    assert details["phone"] == "+995555123456"
    assert details["owner_name"] == "Нино"


def test_detail_page_without_optional_fields(scraper: MyHomeScraper) -> None:
    assert scraper._parse_detail("<html><body><h1>Только заголовок</h1></body></html>") == {
        "title": "Только заголовок"
    }


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 200 ₾", (1200.0, "GEL")),
        ("$800", (800.0, "USD")),
        ("1,000 USD", (1000.0, "USD")),
        ("950 €", (950.0, "EUR")),
        ("договорная", (0.0, "GEL")),
    ],
)
def test_parse_price(scraper: MyHomeScraper, text: str, expected: tuple[float, str]) -> None:
    assert scraper._parse_price(text) == expected


async def test_scrape_merges_details_and_paginates(
    scraper: MyHomeScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = FakePages({list_url(1): LIST_HTML, "/ru/12345/": DETAIL_HTML})
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    listings = await scraper.scrape_listings(limit=10)

    assert len(listings) == 2
    first, second = listings
    # Первая: данные со страницы объявления поверх данных из списка
    assert (first.title, first.price, first.rooms, first.phone, first.owner_name) == (
        "Светлая квартира в Ваке",
        1200.0,
        3,
        "+995555123456",
        "Нино",
    )
    assert len(first.photos) == 2
    # Вторая: страница объявления пустая, данные из списка сохраняются
    assert (second.title, second.price) == ("Test House in Saburtalo", 1500.0)
    # Страница 2 списка пустая: пагинация остановилась
    assert sum(list_url(2) in url for url in pages.requested) == 1
    assert not any(list_url(3) in url for url in pages.requested)


async def test_limit_stops_early(scraper: MyHomeScraper, monkeypatch: pytest.MonkeyPatch) -> None:
    pages = FakePages({list_url(1): LIST_HTML})
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    listings = await scraper.scrape_listings(limit=1)

    assert [item.source_id for item in listings] == ["12345"]
    assert not any(list_url(2) in url for url in pages.requested)
    assert not any("/ru/67890/" in url for url in pages.requested)


async def test_no_details_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    scraper = MyHomeScraper(delay_seconds=0, fetch_details=False)
    pages = FakePages({list_url(1): LIST_HTML})
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    listings = await scraper.scrape_listings(limit=10)

    assert len(listings) == 2
    assert not any("/ru/12345/" in url for url in pages.requested)


async def test_failed_detail_page_keeps_card(
    scraper: MyHomeScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = httpx.ConnectError("boom")
    pages = FakePages({list_url(1): LIST_HTML, "/ru/12345/": error})
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    listings = await scraper.scrape_listings(limit=10)

    titles = [item.title for item in listings]
    assert titles == ["Test Apartment in Vake", "Test House in Saburtalo"]


async def test_failed_list_page_is_skipped(
    scraper: MyHomeScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = FakePages({list_url(1): httpx.ConnectError("boom"), list_url(2): LIST_HTML})
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    listings = await scraper.scrape_listings(limit=10)

    assert len(listings) == 2


async def test_stops_after_consecutive_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    scraper = MyHomeScraper(delay_seconds=0, max_pages=20)
    pages = FakePages({}, default="")
    pages.pages = {"page=": httpx.ConnectError("down")}
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    listings = await scraper.scrape_listings(limit=10)

    assert listings == []
    assert len(pages.requested) == 3


async def test_dump_saves_raw_html(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    scraper = MyHomeScraper(delay_seconds=0, dump_dir=tmp_path / "raw")
    monkeypatch.setattr(
        scraper, "_fetch_page", FakePages({list_url(1): LIST_HTML, "/ru/12345/": DETAIL_HTML})
    )

    await scraper.scrape_listings(limit=2)

    assert (tmp_path / "raw" / "myhome_list.html").read_text(encoding="utf-8") == LIST_HTML
    assert (tmp_path / "raw" / "myhome_detail.html").read_text(encoding="utf-8") == DETAIL_HTML
