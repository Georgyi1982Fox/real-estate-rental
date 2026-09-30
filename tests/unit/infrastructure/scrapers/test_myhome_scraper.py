"""Парсер MyHome.ge на HTML-фикстурах (без сети)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.myhome_scraper import MyHomeScraper

DATA = Path(__file__).parent / "test_data"
LIST_HTML = (DATA / "myhome_test.html").read_text(encoding="utf-8")
DETAIL_HTML = (DATA / "myhome_detail_test.html").read_text(encoding="utf-8")
NEXT_LIST_HTML = (DATA / "myhome_next_list.html").read_text(encoding="utf-8")
EMPTY_HTML = "<html><body>Ничего не найдено</body></html>"
BASE = "https://www.myhome.ge"


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


def list_url(page: int) -> str:
    return f"&page={page}"


@pytest.fixture
def scraper() -> MyHomeScraper:
    return MyHomeScraper(delay_seconds=0, daily_search_paths={}, cities=("tbilisi",))


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


def test_parse_next_data_list_page(scraper: MyHomeScraper) -> None:
    """Настоящая страница сайта (Next.js): объявления берутся из __NEXT_DATA__."""
    listings = scraper._parse_listings(NEXT_LIST_HTML)

    assert [item.source_id for item in listings] == ["26173256", "26117556"]
    first = listings[0]
    assert first.source_name == "myhome"
    assert first.title == "Сдается 3 комнатная квартира в глдани"
    assert first.description == "Vekua 119, недавно отремонтированный"
    # Цена берётся в лари, хотя владелец указал её в долларах
    assert (first.price, first.currency) == (1304.0, "GEL")
    assert (first.rooms, first.area) == (3, 80.0)
    assert first.district == "Глдани"
    assert first.url == f"{BASE}/ru/nedvizhimost/sdaetsia-3-komnatnaia-kvartira-v-gldani-26173256/"
    assert first.owner_name == "Davit"
    assert first.phone is None
    # Главное фото первым, ссылки на большой размер
    assert len(first.photos) == 2
    assert first.photos[0].endswith("/6LlSRkt6ab7fc321e427.webp")
    assert all("_thumb" not in photo and "_blur" not in photo for photo in first.photos)


def next_page(payload: object) -> str:
    return (
        '<html><body><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload, ensure_ascii=False)
        + "</script></body></html>"
    )


def test_parse_next_data_detail_page(scraper: MyHomeScraper) -> None:
    statement = {
        "id": 1,
        "dynamic_title": "Сдается 2 комнатная квартира в ваке",
        "price": {"2": {"price_total": 700}},
        "statement_currency_id": 2,
        "room": "2",
        "area": 60,
        "urban_name": "Ваке",
        "description": "Полное описание квартиры",
        "images": [{"large": "https://img/1.webp", "is_main": True}],
        "phone_number": "+995 555 12-34-56",
        "user_title": "Нино",
    }
    html = next_page({"props": {"pageProps": {"statement": statement}}})

    assert scraper._parse_detail(html) == {
        "title": "Сдается 2 комнатная квартира в ваке",
        "price": 700.0,
        "currency": "USD",
        "district": "Ваке",
        "rooms": 2,
        "area": 60.0,
        "description": "Полное описание квартиры",
        "photos": ["https://img/1.webp"],
        "phone": "+995555123456",
        "owner_name": "Нино",
        "has_details": True,
    }


def test_next_data_detail_skips_masked_phone(scraper: MyHomeScraper) -> None:
    """Настоящая страница объявления: телефон скрыт звёздочками, имя в ``owner_name``."""
    statement = {
        "id": 25375408,
        "dynamic_title": "Сдается 3 комнатная квартира в сабуртало",
        "price": {"1": {"price_total": 1956}, "2": {"price_total": 750}},
        "currency_id": 2,
        "comment": "Сдается в аренду 3-комнатная квартира в Цагареле.",
        "user_phone_number": "591589***",
        "additional_phone_number": "",
        "owner_name": "REALTYSOLUTIONS",
    }
    html = next_page(
        {
            "props": {
                "pageProps": {
                    "dehydratedState": {
                        "queries": [
                            {
                                "queryKey": ["statements", "details"],
                                "state": {"data": {"data": {"statement": statement}}},
                            }
                        ]
                    }
                }
            }
        }
    )

    details = scraper._parse_detail(html)

    assert "phone" not in details
    assert details["owner_name"] == "REALTYSOLUTIONS"
    assert (details["price"], details["currency"]) == (1956.0, "GEL")
    assert details["description"] == "Сдается в аренду 3-комнатная квартира в Цагареле."


def test_next_data_without_statements_falls_back_to_html(scraper: MyHomeScraper) -> None:
    html = LIST_HTML.replace(
        "</body>",
        '<script id="__NEXT_DATA__" type="application/json">{"props": {}}</script></body>',
    )
    assert [item.source_id for item in scraper._parse_listings(html)] == ["12345", "67890"]
    broken = '<script id="__NEXT_DATA__">{not json</script>' + DETAIL_HTML
    assert scraper._parse_detail(broken)["owner_name"] == "Нино"


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
    scraper = MyHomeScraper(
        delay_seconds=0, daily_search_paths={}, cities=("tbilisi",), fetch_details=False
    )
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
    scraper = MyHomeScraper(
        delay_seconds=0, daily_search_paths={}, cities=("tbilisi",), max_pages=20
    )
    pages = FakePages({}, default="")
    pages.pages = {"page=": httpx.ConnectError("down")}
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    listings = await scraper.scrape_listings(limit=10)

    assert listings == []
    assert len(pages.requested) == 3


async def test_dump_saves_raw_html(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    scraper = MyHomeScraper(
        delay_seconds=0, daily_search_paths={}, cities=("tbilisi",), dump_dir=tmp_path / "raw"
    )
    monkeypatch.setattr(
        scraper, "_fetch_page", FakePages({list_url(1): LIST_HTML, "/ru/12345/": DETAIL_HTML})
    )

    await scraper.scrape_listings(limit=2)

    assert (tmp_path / "raw" / "myhome_list.html").read_text(encoding="utf-8") == LIST_HTML
    assert (tmp_path / "raw" / "myhome_detail.html").read_text(encoding="utf-8") == DETAIL_HTML


def test_real_detail_page_extras(scraper: MyHomeScraper) -> None:
    """Реальная страница объявления MyHome (сокращённая): этажи, удобства, адрес, даты."""
    html = Path("tests/unit/infrastructure/scrapers/test_data/myhome_detail_full.html").read_text(
        encoding="utf-8"
    )
    details = scraper._parse_detail(html)

    assert details["has_details"] is True
    assert (details["floor"], details["total_floors"]) == (4, 9)
    assert details["condition"] == "newly_renovated"
    assert details["owner_type"] == "agent"
    assert details["address"] == "ცაგარელის ქუჩა 26"
    assert details["latitude"] == pytest.approx(41.723501)
    assert details["features"] == [
        "furniture",
        "kitchen_appliances",
        "air_conditioning",
        "heating",
        "hot_water",
        "washing_machine",
        "fridge",
        "tv",
        "internet",
        "gas",
        "balcony",
    ]
    assert details["published_at"] == datetime(2026, 7, 6, 12, 18, 18, tzinfo=UTC)
    assert details["updated_at"] == datetime(2026, 9, 27, 8, 8, 19, tzinfo=UTC)
    assert "phone" not in details  # номер на странице скрыт звёздочками


def test_detail_page_of_inactive_listing(scraper: MyHomeScraper) -> None:
    html = Path("tests/unit/infrastructure/scrapers/test_data/myhome_detail_full.html").read_text(
        encoding="utf-8"
    )
    assert "active" not in scraper._parse_detail(html)

    inactive = scraper._parse_detail(html.replace('"is_active": true', '"is_active": false'))
    assert inactive["active"] is False


async def test_stops_when_pages_bring_nothing_new(
    scraper: MyHomeScraper, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Две страницы подряд только с известными объявлениями: дальше старые, стоп."""
    pages = FakePages({"page=": LIST_HTML})
    monkeypatch.setattr(scraper, "_fetch_page", pages)
    checked: list[str] = []

    async def known(card: RawListing) -> bool:
        checked.append(card.source_id)
        return False

    listings = await scraper.scrape_listings(limit=100, needs_details=known)

    assert len(listings) == 4
    assert [url for url in pages.requested if "page=" not in url] == [], "страницы не открывались"
    assert sum("page=" in url for url in pages.requested) == 2


async def test_each_city_has_its_own_search(monkeypatch: pytest.MonkeyPatch) -> None:
    """TASK-079: у myhome.ge у каждого города свой адрес поиска; город — у объявления."""
    scraper = MyHomeScraper(
        delay_seconds=0,
        fetch_details=False,
        search_paths={"tbilisi": "/tbilisi/?page={page}", "batumi": "/batumi/?page={page}"},
        cities=("tbilisi", "batumi"),
    )
    tbilisi = LIST_HTML
    pages = FakePages({"/tbilisi/?page=1": tbilisi, "/batumi/?page=1": tbilisi})
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    listings = await scraper.scrape_listings(limit=10)

    assert sorted(item.city for item in listings) == ["batumi", "batumi", "tbilisi", "tbilisi"]


def test_other_city_in_statement_is_dropped(scraper: MyHomeScraper) -> None:
    html = NEXT_LIST_HTML
    assert {item.city for item in scraper._parse_listings(html, "tbilisi")} == {"tbilisi"}
    kutaisi = html.replace('"city_name": "Тбилиси"', '"city_name": "Кутаиси"')
    assert scraper._parse_listings(kutaisi, "tbilisi") == []
    batumi = html.replace('"city_name": "Тбилиси"', '"city_name": "Батуми"')
    assert scraper._parse_listings(batumi, "tbilisi") == []
    assert {item.city for item in scraper._parse_listings(batumi, "batumi")} == {"batumi"}


def test_disabled_city_is_not_scraped() -> None:
    scraper = MyHomeScraper(delay_seconds=0, daily_search_paths={}, cities=("batumi",))
    assert list(scraper.search_paths) == ["batumi"]


def test_daily_rent_statements() -> None:
    """TASK-092: deal_type_id 7 — посуточная аренда (ищется отдельным адресом)."""
    scraper = MyHomeScraper(delay_seconds=0, cities=("tbilisi",))
    assert list(scraper.daily_search_paths) == ["tbilisi"]
    assert "deal_types=7" in scraper.daily_search_paths["tbilisi"]
    assert MyHomeScraper(delay_seconds=0, search_path="/x").daily_search_paths == {}

    monthly = scraper._parse_listings(NEXT_LIST_HTML)
    assert {item.rent_period for item in monthly} == {"monthly"}
    html = NEXT_LIST_HTML.replace('"deal_type_id": 2', '"deal_type_id": 7')
    assert {item.rent_period for item in scraper._parse_listings(html)} == {"daily"}
