import dataclasses
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from bina.application.listing_details import clean_features
from bina.application.ports.scraper import NeedsDetails, RawListing
from bina.infrastructure.scrapers.base_scraper import (
    KNOWN_PAGES_TO_STOP,
    BaseWebsiteScraper,
    ListingGoneError,
)
from bina.infrastructure.scrapers.details import (
    condition_code,
    owner_type_code,
    to_datetime,
    to_float,
    to_int,
)
from bina.infrastructure.scrapers.nextjs import next_data, walk
from bina.infrastructure.scrapers.settings import MyHomeSelectors, MyHomeSettings

logger = structlog.get_logger(__name__)

SOURCE_NAME = "myhome"
# Ключи цен в JSON сайта: price["1"] в лари, "2" в долларах, "3" в евро
CURRENCY_BY_ID = {"1": "GEL", "2": "USD", "3": "EUR"}
# После стольких ошибок страниц списка подряд парсинг останавливается
MAX_CONSECUTIVE_FAILURES = 3


class MyHomeScraper(BaseWebsiteScraper):
    """Парсер объявлений с MyHome.ge.

    Два этапа: страницы списка (id, ссылка, краткие данные), затем страница
    каждого объявления (полное описание, все фото, телефон, имя арендодателя).

    Сайт написан на Next.js: данные объявлений лежат в странице JSON-ом
    (``<script id="__NEXT_DATA__">``). Он читается в первую очередь; разбор HTML
    по селекторам остаётся запасным вариантом.
    """

    def __init__(
        self,
        base_url: str = MyHomeSettings.BASE_URL,
        delay_seconds: int = 2,
        user_agents: list[str] | None = None,
        *,
        selectors: MyHomeSelectors = MyHomeSettings.SELECTORS,
        search_path: str = MyHomeSettings.SEARCH_PATH,
        max_pages: int = MyHomeSettings.MAX_PAGES,
        fetch_details: bool = True,
        dump_dir: Path | None = None,
    ) -> None:
        super().__init__(base_url, delay_seconds, user_agents)
        self.selectors = selectors
        self.search_path = search_path
        self.max_pages = max_pages
        self.fetch_details = fetch_details
        self.dump_dir = dump_dir

    async def scrape_listings(
        self, limit: int, needs_details: NeedsDetails | None = None
    ) -> list[RawListing]:
        """Парсит до ``limit`` объявлений (список + страницы объявлений)."""
        logger.info("Starting MyHome scraping", limit=limit, details=self.fetch_details)
        listings: list[RawListing] = []
        failures = known_pages = 0

        for page in range(1, self.max_pages + 1):
            if len(listings) >= limit:
                break
            url = self.base_url + self.search_path.format(page=page)
            try:
                html = await self._fetch_page(url)
            except httpx.HTTPError as exc:
                failures += 1
                logger.error("MyHome list page failed", page=page, error=str(exc))
                if failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error("Too many failed pages, stopping", failures=failures)
                    break
                continue
            failures = 0
            if page == 1:
                self._dump("myhome_list.html", html)

            cards = self._parse_listings(html)
            if not cards:
                logger.info("No more listings on MyHome", page=page)
                break
            fresh = await self._add_cards(cards, listings, limit, needs_details)
            known_pages = 0 if fresh or needs_details is None else known_pages + 1
            if known_pages >= KNOWN_PAGES_TO_STOP:
                logger.info("No new or changed listings on MyHome, stopping", page=page)
                break

        logger.info("Finished MyHome scraping", total=len(listings))
        return listings

    async def with_details(self, card: RawListing, *, first: bool = False) -> RawListing:
        """Дополняет карточку данными со страницы объявления (при ошибке оставляет как есть)."""
        if not self.fetch_details or not card.url:
            return card
        try:
            html = await self._fetch_page(card.url, expect=card.source_id)
        except (httpx.HTTPError, ListingGoneError) as exc:
            logger.warning("MyHome detail page failed", url=card.url, error=str(exc))
            return card
        if first:
            self._dump("myhome_detail.html", html)
        try:
            details = self._parse_detail(html)
        except (ValueError, AttributeError) as exc:
            logger.warning("MyHome detail page not parsed", url=card.url, error=str(exc))
            return card
        return dataclasses.replace(card, **details)

    def _dump(self, filename: str, html: str) -> None:
        """Сохраняет сырой HTML для сверки селекторов с реальным сайтом."""
        if self.dump_dir is None:
            return
        self.dump_dir.mkdir(parents=True, exist_ok=True)
        path = self.dump_dir / filename
        path.write_text(html, encoding="utf-8")
        logger.info("Saved raw HTML", path=str(path))

    # ------------------------------------------------------------------ list page

    def _parse_listings(self, html: str) -> list[RawListing]:
        """Карточки со страницы списка: из JSON Next.js, иначе из HTML."""
        data = next_data(html)
        if data is not None:
            statements = [item for items in _statement_lists(data) for item in items]
            if statements:
                return [self._from_statement(item) for item in statements]
        return self._parse_listings_html(html)

    def _from_statement(self, item: dict[str, Any]) -> RawListing:
        """Объявление из JSON-объекта ``statement`` сайта."""
        price, currency = _statement_price(item)
        listing_id = str(item["id"])
        slug = str(item.get("dynamic_slug") or "")
        path = f"/ru/nedvizhimost/{slug}-{listing_id}/" if slug else f"/ru/pr/{listing_id}/"
        return RawListing(
            source_id=listing_id,
            source_name=SOURCE_NAME,
            title=str(item.get("dynamic_title") or "").strip(),
            description=str(item.get("comment") or "").strip(),
            price=price,
            currency=currency,
            rooms=_parse_rooms(str(item.get("room") or "")),
            area=float(item.get("area") or 0),
            district=str(item.get("urban_name") or item.get("district_name") or "Unknown"),
            url=self.base_url + path,
            photos=_statement_photos(item),
            owner_name=str(item.get("user_title") or "").strip() or None,
            **_statement_extras(item),
        )

    def _parse_listings_html(self, html: str) -> list[RawListing]:
        """Карточки со страницы списка по CSS-селекторам."""
        soup = BeautifulSoup(html, "lxml")
        s = self.selectors
        listings: list[RawListing] = []

        for element in soup.select(s.card):
            listing_id = str(element.get(s.card_id_attr) or "").strip()
            if not listing_id:
                continue
            link = element.select_one(s.card_link)
            href = str(link.get("href") or "") if link else ""
            price, currency = self._parse_price(_text(element, s.card_price) or "0")
            description = _text(element, s.card_description)
            image = element.select_one(s.card_image)
            photo = str(image.get("src") or image.get("data-src") or "") if image else ""

            listings.append(
                RawListing(
                    source_id=listing_id,
                    source_name=SOURCE_NAME,
                    title=link.get_text(strip=True) if link else "",
                    description=description,
                    price=price,
                    currency=currency,
                    rooms=_parse_rooms(_text(element, s.card_rooms)),
                    area=_parse_area(_text(element, s.card_area)),
                    district=_text(element, s.card_district) or "Unknown",
                    url=urljoin(self.base_url + "/", href) if href else "",
                    photos=[urljoin(self.base_url + "/", photo)] if photo else [],
                )
            )
        return listings

    # ---------------------------------------------------------------- detail page

    def details_from_html(self, html: str) -> dict[str, Any] | None:
        """Поля ``RawListing`` со страницы объявления; None — страница не разобрана."""
        try:
            details = self._parse_detail(html)
        except (ValueError, AttributeError):
            return None
        return details or None

    def _parse_detail(self, html: str) -> dict[str, Any]:
        """Поля со страницы объявления; отсутствующие на странице не возвращаются."""
        data = next_data(html)
        if data is not None:
            statement = _find_statement(data)
            if statement is not None:
                return _statement_details(statement)
        return self._parse_detail_html(html)

    def _parse_detail_html(self, html: str) -> dict[str, Any]:
        """Поля страницы объявления по CSS-селекторам."""
        soup = BeautifulSoup(html, "lxml")
        s = self.selectors
        details: dict[str, Any] = {}

        if title := _text(soup, s.detail_title):
            details["title"] = title
        if price_text := _text(soup, s.detail_price):
            price, currency = self._parse_price(price_text)
            if price > 0:
                details["price"], details["currency"] = price, currency
        if district := _text(soup, s.detail_district):
            details["district"] = district
        if rooms := _parse_rooms(_text(soup, s.detail_rooms)):
            details["rooms"] = rooms
        if area := _parse_area(_text(soup, s.detail_area)):
            details["area"] = area
        if description := _text(soup, s.detail_description, separator="\n"):
            details["description"] = description

        photos: list[str] = []
        for image in soup.select(s.detail_photos):
            src = str(image.get("data-src") or image.get("src") or "")
            url = urljoin(self.base_url + "/", src) if src else ""
            if url and url not in photos:
                photos.append(url)
        if photos:
            details["photos"] = photos

        phone_element = soup.select_one(s.detail_phone)
        if phone_element is not None:
            raw_phone = str(phone_element.get("data-phone") or phone_element.get_text(strip=True))
            if phone := _clean_phone(raw_phone):
                details["phone"] = phone
        if owner := _text(soup, s.detail_owner):
            details["owner_name"] = owner
        return details

    def _parse_price(self, price_text: str) -> tuple[float, str]:
        """Цена и валюта из текста: ``1 200 ₾``, ``$800``, ``1,000 USD``."""
        compact = price_text.replace(",", "").replace(" ", "").replace("\xa0", "")
        currency = "GEL"
        if "USD" in compact or "$" in compact:
            currency = "USD"
        elif "EUR" in compact or "€" in compact:
            currency = "EUR"
        match = re.search(r"\d+(?:\.\d+)?", compact)
        return (float(match.group()) if match else 0.0), currency


def _text(root: BeautifulSoup | Tag, selector: str, separator: str = " ") -> str:
    """Текст первого элемента по селектору (пустая строка, если не найден)."""
    element = root.select_one(selector)
    return element.get_text(separator, strip=True) if element else ""


def _parse_rooms(text: str) -> int:
    """Количество комнат: ``2 комнаты``, ``3 room``, ``2 ოთახი``."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def _parse_area(text: str) -> float:
    """Площадь в м²: ``50 м²``, ``72.5 m²``."""
    match = re.search(r"(\d+(?:[.,]\d+)?)", text)
    return float(match.group(1).replace(",", ".")) if match else 0.0


def _clean_phone(text: str) -> str:
    """Телефон без лишних символов: ``+995 555 12-34-56`` → ``+995555123456``."""
    digits = re.sub(r"[^\d+]", "", text)
    return digits if len(re.sub(r"\D", "", digits)) >= 6 else ""


# ------------------------------------------------------------------ JSON Next.js


def _is_statement(value: Any) -> bool:
    """Похоже ли значение на объявление сайта."""
    return (
        isinstance(value, dict)
        and "id" in value
        and "price" in value
        and ("dynamic_title" in value or "room" in value)
    )


def _statement_lists(data: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
    """Списки объявлений в JSON страницы поиска."""
    for value in walk(data):
        if isinstance(value, list) and value and all(_is_statement(item) for item in value):
            yield value


def _find_statement(data: dict[str, Any]) -> dict[str, Any] | None:
    """Первое объявление в JSON страницы объявления."""
    for value in walk(data):
        if _is_statement(value):
            return dict(value)
    return None


def _statement_price(item: dict[str, Any]) -> tuple[float, str]:
    """Цена в лари, если она есть, иначе в валюте объявления."""
    prices = item.get("price")
    if not isinstance(prices, dict):
        return 0.0, "GEL"
    currency_id = str(item.get("statement_currency_id") or item.get("currency_id") or "1")
    for key in ("1", currency_id):
        entry = prices.get(key)
        if isinstance(entry, dict) and entry.get("price_total"):
            return float(entry["price_total"]), CURRENCY_BY_ID.get(key, "GEL")
    return 0.0, "GEL"


def _statement_photos(item: dict[str, Any]) -> list[str]:
    """Ссылки на фото в большом размере, главное первым."""
    images = item.get("images")
    if not isinstance(images, list):
        return []
    ordered = sorted(
        (image for image in images if isinstance(image, dict)),
        key=lambda image: not image.get("is_main"),
    )
    photos: list[str] = []
    for image in ordered:
        url = str(image.get("large") or image.get("thumb") or "")
        if url and url not in photos:
            photos.append(url)
    return photos


def _statement_details(item: dict[str, Any]) -> dict[str, Any]:
    """Поля объявления со страницы объявления (только найденные)."""
    details: dict[str, Any] = {}
    if title := str(item.get("dynamic_title") or "").strip():
        details["title"] = title
    price, currency = _statement_price(item)
    if price > 0:
        details["price"], details["currency"] = price, currency
    if district := str(item.get("urban_name") or item.get("district_name") or ""):
        details["district"] = district
    if rooms := _parse_rooms(str(item.get("room") or "")):
        details["rooms"] = rooms
    if area := float(item.get("area") or 0):
        details["area"] = area
    description = item.get("description") or item.get("comment")
    if isinstance(description, str) and description.strip():
        details["description"] = description.strip()
    if photos := _statement_photos(item):
        details["photos"] = photos
    # Сайт отдаёт номер замаскированным (``591589***``), полный только по кнопке: такие пропускаем
    for key in ("phone", "phone_number", "user_phone_number"):
        raw = item.get(key)
        if isinstance(raw, str | int) and "*" not in str(raw) and (phone := _clean_phone(str(raw))):
            details["phone"] = phone
            break
    if owner := str(item.get("user_title") or item.get("owner_name") or "").strip():
        details["owner_name"] = owner
    details.update(_statement_extras(item))
    details["has_details"] = True
    if item.get("is_active") is False:
        # Снято владельцем или истёк срок
        details["active"] = False
    return details


# Параметры (``parameters[].key``) страницы объявления → наши коды удобств
_MYHOME_FEATURES: dict[str, str] = {
    "furniture": "furniture",
    "kitchen": "kitchen_appliances",
    "conditioner": "air_conditioning",
    "air_conditioner": "air_conditioning",
    "heating": "heating",
    "hot_water": "hot_water",
    "washing_machine": "washing_machine",
    "dishwasher": "dishwasher",
    "refrigerator": "fridge",
    "tv": "tv",
    "internet": "internet",
    "wifi": "internet",
    "gas": "gas",
    "elevator": "elevator",
    "lift": "elevator",
    "parking": "parking",
    "garage": "parking",
    "balcony": "balcony",
    "loggia": "balcony",
    "storeroom": "storage",
    "pool": "pool",
    "swimming_pool": "pool",
    "pets": "pets_allowed",
    "pets_allowed": "pets_allowed",
    "alarm": "security",
    "security": "security",
}


def _statement_extras(item: dict[str, Any]) -> dict[str, Any]:
    """Этажи, спальни, удобства, состояние, адрес, даты (из списка и страницы объявления)."""
    extras: dict[str, Any] = {}
    user_type = item.get("user_type")
    for key, value in (
        ("floor", to_int(item.get("floor"))),
        ("total_floors", to_int(item.get("total_floors"))),
        ("bedrooms", to_int(item.get("bedroom"))),
        ("condition", condition_code(item.get("condition"))),
        (
            "owner_type",
            owner_type_code(user_type.get("type") if isinstance(user_type, dict) else None),
        ),
        ("address", str(item.get("address") or "").strip() or None),
        ("latitude", to_float(item.get("lat"))),
        ("longitude", to_float(item.get("lng"))),
        ("published_at", to_datetime(item.get("created_at"))),
        ("updated_at", to_datetime(item.get("last_updated"))),
    ):
        if value is not None:
            extras[key] = value

    parameters = item.get("parameters")
    if isinstance(parameters, list) and parameters:
        codes = [
            _MYHOME_FEATURES[str(parameter.get("key"))]
            for parameter in parameters
            if isinstance(parameter, dict) and str(parameter.get("key")) in _MYHOME_FEATURES
        ]
        if to_int(item.get("balconies")):
            codes.append("balcony")
        for key, code in (
            ("heating_type_id", "heating"),
            ("hot_water_type_id", "hot_water"),
            ("parking_type_id", "parking"),
        ):
            if item.get(key):
                codes.append(code)
        extras["features"] = clean_features(codes)
    return extras
