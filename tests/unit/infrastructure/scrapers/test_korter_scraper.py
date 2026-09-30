"""Парсер Korter.ge (TASK-092) на сохранённых страницах (без сети)."""

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.korter_scraper import KorterScraper, initial_state

DATA = Path(__file__).parent / "test_data"
LIST_HTML = (DATA / "korter_list.html").read_text(encoding="utf-8")
DAILY_HTML = (DATA / "korter_daily_list.html").read_text(encoding="utf-8")
DETAIL_HTML = (DATA / "korter_detail.html").read_text(encoding="utf-8")
EMPTY_HTML = "<html><body>no data</body></html>"
BASE = "https://korter.ge"


class FakePages:
    """Подменяет ``_fetch_page``: URL → HTML или исключение; записывает запросы."""

    def __init__(self, pages: dict[str, str | Exception], default: str = EMPTY_HTML) -> None:
        self.pages = pages
        self.default = default
        self.requested: list[str] = []

    async def __call__(self, url: str, expect: str | None = None) -> str:
        self.requested.append(url)
        for key, value in self.pages.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        return self.default


@pytest.fixture
def korter() -> KorterScraper:
    return KorterScraper(
        delay_seconds=0,
        search_paths={"tbilisi": "/rent-tbilisi?page={page}"},
        cities=("tbilisi",),
    )


def test_default_sections_cover_cities_and_daily_rent() -> None:
    scraper = KorterScraper(delay_seconds=0, cities=("tbilisi", "batumi"))
    assert [city for city, _ in scraper.searches] == ["tbilisi", "batumi", "tbilisi", "batumi"]
    only_batumi = KorterScraper(delay_seconds=0, cities=("batumi",))
    assert [city for city, _ in only_batumi.searches] == ["batumi", "batumi"]


def test_initial_state() -> None:
    state = initial_state(LIST_HTML)
    assert state is not None and "apartmentListingStore" in state
    assert initial_state(EMPTY_HTML) is None
    assert initial_state("<script>window.INITIAL_STATE = {broken</script>") is None


def test_list_page(korter: KorterScraper) -> None:
    cards = korter.parse_list(LIST_HTML, "tbilisi")

    assert [card.source_id for card in cards] == ["930648", "930628", "750321"], "дом — не берём"
    first = cards[0]
    assert first.source_name == "korter"
    assert first.title == "3-комнатная квартира, Крцаниси"
    assert (first.price, first.currency, first.rent_period) == (1200.0, "USD", "monthly")
    assert (first.rooms, first.area, first.floor, first.total_floors) == (3, 75.0, 9, 12)
    assert (first.district, first.city) == ("Крцаниси", "tbilisi")
    assert first.address == "ул. Вахтанга Горгасали, 61"
    assert first.latitude == pytest.approx(41.67793443)
    assert first.url.startswith(f"{BASE}/ru/%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B0")
    assert first.url.endswith("/krtsanisi-modern/930648")
    assert first.photos and first.photos[0].startswith("https://storage.googleapis.com/")
    assert first.updated_at == datetime(2026, 9, 30, 12, 26, 16, tzinfo=UTC)


def test_daily_list_page(korter: KorterScraper) -> None:
    cards = korter.parse_list(DAILY_HTML, "tbilisi")

    assert [(card.source_id, card.price, card.currency) for card in cards] == [
        ("614262", 70.0, "GEL"),
        ("606675", 110.0, "GEL"),
    ]
    assert {card.rent_period for card in cards} == {"daily"}


def test_detail_page(korter: KorterScraper) -> None:
    details = korter.details_from_html(DETAIL_HTML)

    assert details is not None
    assert details["has_details"] is True
    assert details["description"] == "Сдаётся квартира с видом на город.\nМебель и техника."
    assert len(details["photos"]) == 3
    assert details["photos"][0].endswith("/realty/1280x960/9151438.jpg")
    assert (details["rooms"], details["bedrooms"], details["bathrooms"]) == (3, 2, 1)
    assert details["features"] == ["balcony"]
    assert (details["owner_name"], details["owner_type"]) == ("Лилия", "agent")
    assert details["phone"] == "+995555000001", "основной номер, без пробелов"
    assert details["published_at"] == datetime(2026, 9, 30, 12, 26, 16, tzinfo=UTC)
    assert "active" not in details


def test_detail_page_rented_and_junk(korter: KorterScraper) -> None:
    rented = korter.details_from_html(
        DETAIL_HTML.replace('"available": "yes"', '"available": "no"')
    )
    assert rented is not None and rented["active"] is False
    assert korter.details_from_html(EMPTY_HTML) is None
    assert korter.details_from_html(LIST_HTML) is None


async def test_scrape_pages_details_and_stop(
    korter: KorterScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = FakePages({"page=1": LIST_HTML, "page=2": LIST_HTML, "/930": DETAIL_HTML})
    pages.pages["/750321"] = DETAIL_HTML
    monkeypatch.setattr(korter, "_fetch_page", pages)

    listings = await korter.scrape_listings(limit=100)

    assert [card.source_id for card in listings] == ["930648", "930628", "750321"]
    assert all(card.has_details for card in listings)
    list_requests = [url for url in pages.requested if "page=" in url]
    assert list_requests == [f"{BASE}/rent-tbilisi?page=1", f"{BASE}/rent-tbilisi?page=2"], (
        "вторая страница — та же, что первая: конец выдачи"
    )


async def test_limit_and_known_listings(
    korter: KorterScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = FakePages({}, default=LIST_HTML)
    monkeypatch.setattr(korter, "_fetch_page", pages)

    async def known(card: RawListing) -> bool:
        return False

    listings = await korter.scrape_listings(limit=2, needs_details=known)

    assert len(listings) == 2
    assert not any(card.has_details for card in listings)


async def test_failed_pages_and_details(
    korter: KorterScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    failing = FakePages({"page=": httpx.ConnectError("down")})
    monkeypatch.setattr(korter, "_fetch_page", failing)
    assert await korter.scrape_listings(limit=10) == []
    assert len(failing.requested) == 3

    card = korter.parse_list(LIST_HTML, "tbilisi")[0]
    monkeypatch.setattr(korter, "_fetch_page", FakePages({}, default=EMPTY_HTML))
    assert await korter.with_details(card) is card
