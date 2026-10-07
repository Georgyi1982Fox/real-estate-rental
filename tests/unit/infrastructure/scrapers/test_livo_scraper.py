"""Парсер Livo.ge (TASK-092) на сохранённых ответах API (без сети)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.livo_scraper import LivoScraper, list_items, page_statements

DATA = Path(__file__).parent / "test_data"
LIST_JSON = (DATA / "livo_list.json").read_text(encoding="utf-8")
DETAIL_JSON = (DATA / "livo_detail.json").read_text(encoding="utf-8")
EMPTY_JSON = json.dumps({"result": True, "data": {"data": []}})
API = "https://api-statements.tnet.ge"


class FakeApi:
    """Подменяет ``BaseWebsiteScraper._fetch_page``: URL → ответ; записывает запросы."""

    def __init__(self, pages: dict[str, str | Exception], default: str = EMPTY_JSON) -> None:
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


def scraper(**kwargs: Any) -> LivoScraper:
    return LivoScraper(delay_seconds=0, **kwargs)


def patch_fetch(monkeypatch: pytest.MonkeyPatch, api: FakeApi) -> None:
    """Подмена сетевого запроса базового класса (перевод адресов сайта в API остаётся)."""
    monkeypatch.setattr(
        "bina.infrastructure.scrapers.base_scraper.BaseWebsiteScraper._fetch_page",
        lambda self, url, expect=None: api(url, expect),
    )


def test_request_headers_and_query() -> None:
    livo = scraper(cities=("tbilisi", "batumi"))
    assert livo.headers["X-Website-Key"] == "livo"
    assert livo.headers["locale"] == "ru"
    assert "cities=1,15" in livo.search_query
    assert "deal_types=2,7" in livo.search_query
    assert "cities=1&" in scraper(cities=("tbilisi",)).search_query


def test_list_cards_from_real_response() -> None:
    livo = scraper()
    cards = [livo.card(item) for item in list_items(LIST_JSON)]

    assert [card.source_id for card in cards] == [
        "26209012",
        "353894",
        "26209293",
        "26209291",
        "26203309",
        "26209260",
    ]
    first = cards[0]
    assert first.source_name == "livo"
    assert first.title == "Сдается 1 комнатная квартира в диди дигоми"
    assert (first.price, first.currency) == (750.0, "GEL")
    assert (first.rooms, first.area) == (1, 25.0)
    assert (first.district, first.city, first.rent_period) == ("Диди Дигоми", "tbilisi", "monthly")
    assert first.url.startswith("https://livo.ge/udzravi-qoneba/")
    assert first.url.endswith("-26209012")
    assert first.photos[0].startswith("https://static-api-statements.tnet.ge/")
    assert first.owner_name == "Нино"


def test_daily_rent_and_batumi() -> None:
    livo = scraper()
    cards = {card.source_id: card for card in map(livo.card, list_items(LIST_JSON))}

    daily = cards["353894"]
    assert (daily.rent_period, daily.price, daily.district) == ("daily", 50.0, "Варкетили")
    batumi = cards["26209260"]
    # Район в Батуми часто не указан: объявление относится к городу в целом
    assert (batumi.city, batumi.district, batumi.rent_period) == ("batumi", "Батуми", "monthly")
    assert cards["26203309"].rent_period == "daily"


def test_detail_response() -> None:
    details = scraper().details_from_html(DETAIL_JSON)

    assert details is not None
    assert details["has_details"] is True
    assert details["title"] == "Сдается 2 комнатная квартира в ведзиси"
    assert details["rooms"] == 2, "в объявлении нет room — число из room_type_id"
    assert details["rent_period"] == "monthly"
    assert details["latitude"] == 41.732425
    assert details["description"].startswith("Сдается в аренду в Ведзиси"), (
        "перевод сайта (locale: ru)"
    )
    assert "phone" not in details, "замаскированный номер (555000***) не сохраняется"
    assert details["owner_type"] == "owner"
    assert details["published_at"] == datetime(2026, 9, 28, 16, 45, 28, tzinfo=UTC)
    assert "active" not in details


def test_detail_inactive_and_junk() -> None:
    livo = scraper()
    data = json.loads(DETAIL_JSON)
    data["data"]["statement"]["is_active"] = False
    details = livo.details_from_html(json.dumps(data))
    assert details is not None and details["active"] is False
    assert livo.details_from_html("<html>not json</html>") is None
    assert livo.details_from_html(json.dumps({"result": False, "data": []})) is None


async def test_scrape_pages_and_details(monkeypatch: pytest.MonkeyPatch) -> None:
    livo = scraper(max_pages=5)
    api = FakeApi({"page=1": LIST_JSON, "/v1/statements/": DETAIL_JSON})
    patch_fetch(monkeypatch, api)

    listings = await livo.scrape_listings(limit=100)

    assert len(listings) == 6
    assert all(card.has_details for card in listings)
    list_requests = [url for url in api.requested if "page=" in url]
    assert list_requests[0].startswith("https://livo.ge/ru/s?deal_types=2,7")
    assert len(list_requests) == 2, "пустая вторая страница — конец выдачи"
    assert f"{API}/v1/statements/26209012" in api.requested


async def test_known_regular_listings_stop_scraping(monkeypatch: pytest.MonkeyPatch) -> None:
    """Страницы только с известными объявлениями — дальше старые (VIP в счёт не идут)."""
    livo = scraper(max_pages=10, fetch_details=False)
    api = FakeApi({}, default=LIST_JSON)
    patch_fetch(monkeypatch, api)

    async def known(card: RawListing) -> bool:
        return False

    await livo.scrape_listings(limit=1000, needs_details=known)

    assert len([url for url in api.requested if "page=" in url]) == 2


async def test_failed_pages_stop_after_three(monkeypatch: pytest.MonkeyPatch) -> None:
    livo = scraper(max_pages=10)
    failing = FakeApi({"page=": httpx.ConnectError("down")})
    patch_fetch(monkeypatch, failing)

    assert await livo.scrape_listings(limit=10) == []
    assert len(failing.requested) == 3


async def test_detail_failure_keeps_card(monkeypatch: pytest.MonkeyPatch) -> None:
    livo = scraper()
    card = livo.card(list_items(LIST_JSON)[0])
    patch_fetch(monkeypatch, FakeApi({"/v1/statements/": httpx.ConnectError("down")}))

    assert await livo.with_details(card) is card


async def test_recheck_reads_listing_page_through_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Перепроверка старых объявлений (TASK-018) открывает адрес сайта — читается API."""
    livo = scraper()
    api = FakeApi({"/v1/statements/26187474": DETAIL_JSON})
    patch_fetch(monkeypatch, api)

    body = await livo._fetch_page(
        "https://livo.ge/udzravi-qoneba/sdaetsia-kvartira/sdaetsia-kvartira-26187474",
        expect="26187474",
    )

    assert api.requested == [f"{API}/v1/statements/26187474"]
    assert livo.details_from_html(body) is not None


def search_page(items: list[dict[str, Any]]) -> str:
    """Страница поиска сайта: объявления в данных Next.js, разбитые на куски."""
    payload = json.dumps({"statements": {"data": items, "current_page": 1}})
    middle = len(payload) // 2
    chunks = [f"1:{payload[:middle]}", payload[middle:]]
    pushes = "".join(
        f"<script>self.__next_f.push([1,{json.dumps(chunk)}])</script>" for chunk in chunks
    )
    return f"<!DOCTYPE html><html><body><div>…</div>{pushes}</body></html>"


def test_cards_from_search_page() -> None:
    """С октября 2026 список берётся со страницы сайта: API списка без входа — 401."""
    items = list_items(LIST_JSON)
    html = search_page(items)

    found = list_items(html)

    assert [item["id"] for item in found] == [item["id"] for item in items]
    livo = scraper()
    assert [livo.card(item) for item in found] == [livo.card(item) for item in items]
    assert page_statements("<html>no data</html>") == []


async def test_scrape_search_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    livo = scraper(max_pages=5, fetch_details=False)
    api = FakeApi({"page=1": search_page(list_items(LIST_JSON))}, default=search_page([]))
    patch_fetch(monkeypatch, api)

    listings = await livo.scrape_listings(limit=100)

    assert len(listings) == 6
    assert api.requested[0].startswith("https://livo.ge/ru/s?")
