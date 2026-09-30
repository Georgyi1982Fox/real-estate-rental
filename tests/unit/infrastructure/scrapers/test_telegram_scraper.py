"""Telegram-каналы как источник объявлений (TASK-091), без сети и без AI."""

import dataclasses
from pathlib import Path

import pytest

from bina.application.ports.listing_extractor import ExtractedListing, IListingExtractor
from bina.application.ports.scraper import RawListing
from bina.infrastructure.llm.listing_extractor import parse_extracted, parse_number
from bina.infrastructure.scrapers.telegram_scraper import (
    TelegramChannelScraper,
    apply_extracted,
    parse_channel_page,
    post_card,
)

DATA = Path(__file__).parent / "test_data"
CHANNEL_HTML = (DATA / "tg_channel.html").read_text(encoding="utf-8")
OLD_HTML = (DATA / "tg_channel_old.html").read_text(encoding="utf-8")
EMPTY_HTML = "<html><body></body></html>"
RENTAL = ExtractedListing(
    is_rental_offer=True,
    city="Tbilisi",
    district="Ортачала",
    price=750,
    currency="USD",
    rooms=2,
    bedrooms=1,
    area=68,
    features=["air_conditioning", "dishwasher"],
    title="2-комн. квартира в Ортачала, 68 м²",
)


class FakeExtractor(IListingExtractor):
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def extract(self, text: str) -> ExtractedListing:
        self.texts.append(text)
        if "Ищете жильё" in text:
            return ExtractedListing(is_rental_offer=False)
        return RENTAL


class FakePages:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    async def __call__(self, url: str, expect: str | None = None) -> str:
        self.requested.append(url)
        return self.pages.get(url, EMPTY_HTML)


def test_parse_channel_page() -> None:
    posts, before = parse_channel_page(CHANNEL_HTML, "m2tbilis")

    assert [post.post_id for post in posts] == [73962, 73971, 73972]
    assert before == 73962
    first = posts[0]
    assert first.text.startswith("Ортачала /Надиквари")
    assert "68м2" in first.text and "750$" in first.text
    assert "\n" in first.text, "переносы строк сохраняются"
    assert len(first.photos) == 9
    assert all(url.startswith("https://") for url in first.photos)
    assert first.published_at is not None and first.published_at.tzinfo is not None
    assert posts[1].photos == []

    card = post_card(first)
    assert (card.source_name, card.source_id) == ("telegram", "m2tbilis/73962")
    assert card.url == "https://t.me/m2tbilis/73962"
    assert (card.price, card.has_details) == (0.0, False)


def test_apply_extracted() -> None:
    card = post_card(parse_channel_page(CHANNEL_HTML, "m2tbilis")[0][0])

    listing = apply_extracted(card, RENTAL, "Tbilisi")
    assert (listing.price, listing.currency, listing.rooms, listing.area) == (750, "USD", 2, 68)
    assert (listing.district, listing.bedrooms, listing.has_details) == ("Ортачала", 1, True)
    assert listing.title == "2-комн. квартира в Ортачала, 68 м²"
    assert listing.description == card.description

    for other in (
        ExtractedListing(is_rental_offer=False),
        dataclasses.replace(RENTAL, city="Batumi"),
        dataclasses.replace(RENTAL, area=None),
        dataclasses.replace(RENTAL, district=None),
    ):
        assert apply_extracted(card, other, "Tbilisi") is card


async def test_scrape_sends_only_new_posts_to_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    extractor = FakeExtractor()
    scraper = TelegramChannelScraper(
        extractor, channels=("m2tbilis",), delay_seconds=0, max_age_days=100_000
    )
    pages = FakePages({"https://t.me/s/m2tbilis": CHANNEL_HTML})
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    async def needs(card: RawListing) -> bool:
        return card.source_id != "m2tbilis/73972"  # уже в базе

    listings = await scraper.scrape_listings(limit=50, needs_details=needs)

    # Новые сверху; известный пост AI не отправляется
    assert [item.source_id for item in listings] == [
        "m2tbilis/73972",
        "m2tbilis/73971",
        "m2tbilis/73962",
    ]
    assert len(extractor.texts) == 2
    assert listings[2].has_details and not listings[1].has_details
    # Следующая (более старая) страница
    assert pages.requested[1] == "https://t.me/s/m2tbilis?before=73962"


async def test_old_posts_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Канал, заброшенный в 2022 году: посты старше 21 дня не берутся."""
    extractor = FakeExtractor()
    scraper = TelegramChannelScraper(extractor, channels=("tbilisi_kvartiry",), delay_seconds=0)
    pages = FakePages({"https://t.me/s/tbilisi_kvartiry": OLD_HTML})
    monkeypatch.setattr(scraper, "_fetch_page", pages)

    assert await scraper.scrape_listings(limit=50) == []
    assert extractor.texts == []
    assert len(pages.requested) == 1, "дальше старые — следующая страница не нужна"


def test_parse_extracted() -> None:
    raw = """```json
    {"is_rental_offer": true, "city": "Tbilisi", "district": "Сабуртало", "price": "1 200$",
     "currency": "usd", "rooms": 3, "area": "85 м2", "floor": 5, "total_floors": null,
     "features": ["balcony", "jacuzzi", "furniture"], "title": " 3-комн. "}
    ```"""
    item = parse_extracted(raw)
    assert (item.price, item.currency, item.rooms, item.area) == (1200.0, "USD", 3, 85.0)
    assert item.features == ["furniture", "balcony"]
    assert (item.floor, item.total_floors, item.title) == (5, None, "3-комн.")

    assert not parse_extracted('{"is_rental_offer": false}').is_rental_offer
    with pytest.raises(ValueError):
        parse_extracted("not json")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 200$", 1200.0),
        ("85 м2", 85.0),
        ("80.000$", 80000.0),
        ("1,500 GEL", 1500.0),
        ("65,5 m²", 65.5),
        ("цена 750", 750.0),
        ("договорная", None),
    ],
)
def test_parse_number(text: str, expected: float | None) -> None:
    assert parse_number(text) == expected


def test_batumi_post_in_tbilisi_channel() -> None:
    """TASK-079: пост про Батуми берётся, если Батуми собираем, и получает свой город."""
    card = post_card(parse_channel_page(CHANNEL_HTML, "m2tbilis")[0][0])
    batumi = dataclasses.replace(RENTAL, city="Батуми")
    assert apply_extracted(card, batumi, "Tbilisi") is card
    listing = apply_extracted(card, batumi, "Tbilisi", ("tbilisi", "batumi"))
    assert listing.city == "batumi"
    assert apply_extracted(card, RENTAL, "Tbilisi").city == "tbilisi"
