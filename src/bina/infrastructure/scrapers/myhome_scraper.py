import dataclasses
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from bina.application.cities import DEFAULT_CITY
from bina.application.ports.scraper import NeedsDetails, RawListing
from bina.infrastructure.scrapers.base_scraper import (
    KNOWN_PAGES_TO_STOP,
    BaseWebsiteScraper,
    ListingGoneError,
)
from bina.infrastructure.scrapers.nextjs import next_data
from bina.infrastructure.scrapers.settings import CITIES, MyHomeSelectors, MyHomeSettings
from bina.infrastructure.scrapers.tnet import (
    clean_phone,
    find_statement,
    parse_rooms,
    statement_city,
    statement_details,
    statement_district,
    statement_extras,
    statement_lists,
    statement_photos,
    statement_price,
)

logger = structlog.get_logger(__name__)

SOURCE_NAME = "myhome"
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
        search_path: str | None = None,
        search_paths: dict[str, str] | None = None,
        daily_search_paths: dict[str, str] | None = None,
        cities: tuple[str, ...] = CITIES,
        max_pages: int = MyHomeSettings.MAX_PAGES,
        fetch_details: bool = True,
        dump_dir: Path | None = None,
    ) -> None:
        super().__init__(base_url, delay_seconds, user_agents)
        self.selectors = selectors
        # Город → адрес поиска (у myhome.ge у каждого города свой); ``search_path`` —
        # один адрес для Тбилиси (тесты, ручной запуск)
        paths = search_paths or (
            {DEFAULT_CITY: search_path} if search_path else MyHomeSettings.SEARCH_PATHS
        )
        self.search_paths = {city: paths[city] for city in cities if city in paths}
        # Посуточная аренда (TASK-092); при своих адресах поиска — только если заданы явно,
        # ``{}`` — не собирать
        explicit = search_path is not None or search_paths is not None
        daily = daily_search_paths
        if daily is None:
            daily = {} if explicit else MyHomeSettings.DAILY_SEARCH_PATHS
        self.daily_search_paths = {city: daily[city] for city in cities if city in daily}
        self.max_pages = max_pages
        self.fetch_details = fetch_details
        self.dump_dir = dump_dir

    async def scrape_listings(
        self, limit: int, needs_details: NeedsDetails | None = None
    ) -> list[RawListing]:
        """Парсит до ``limit`` объявлений каждого города (список + страницы объявлений)."""
        logger.info("Starting MyHome scraping", limit=limit, details=self.fetch_details)
        listings: list[RawListing] = []
        searches = [*self.search_paths.items(), *self.daily_search_paths.items()]
        for city, path in searches:
            listings += await self._scrape_city(city, path, limit, needs_details)
        logger.info("Finished MyHome scraping", total=len(listings))
        return listings

    async def _scrape_city(
        self, city: str, search_path: str, limit: int, needs_details: NeedsDetails | None
    ) -> list[RawListing]:
        listings: list[RawListing] = []
        failures = known_pages = 0

        for page in range(1, self.max_pages + 1):
            if len(listings) >= limit:
                break
            url = self.base_url + search_path.format(page=page)
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
                suffix = "" if city == DEFAULT_CITY else f"_{city}"
                self._dump(f"myhome_list{suffix}.html", html)

            cards = self._parse_listings(html, city)
            if not cards:
                logger.info("No more listings on MyHome", page=page, city=city)
                break
            fresh = await self._add_cards(cards, listings, limit, needs_details)
            known_pages = 0 if fresh or needs_details is None else known_pages + 1
            if known_pages >= KNOWN_PAGES_TO_STOP:
                logger.info("No new or changed listings on MyHome, stopping", page=page, city=city)
                break
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

    def _parse_listings(self, html: str, city: str = DEFAULT_CITY) -> list[RawListing]:
        """Карточки со страницы списка города: из JSON Next.js, иначе из HTML.

        Объявления другого города (сайт иногда подмешивает) отбрасываются.
        """
        data = next_data(html)
        if data is not None:
            statements = [item for items in statement_lists(data) for item in items]
            if statements:
                cards = [self._from_statement(item, city) for item in statements]
                return [card for card in cards if card.city == city]
        return [dataclasses.replace(card, city=city) for card in self._parse_listings_html(html)]

    def _from_statement(self, item: dict[str, Any], city: str = DEFAULT_CITY) -> RawListing:
        """Объявление из JSON-объекта ``statement`` сайта."""
        price, currency = statement_price(item)
        listing_id = str(item["id"])
        slug = str(item.get("dynamic_slug") or "")
        path = f"/ru/nedvizhimost/{slug}-{listing_id}/" if slug else f"/ru/pr/{listing_id}/"
        code = statement_city(item, city)
        return RawListing(
            source_id=listing_id,
            source_name=SOURCE_NAME,
            title=str(item.get("dynamic_title") or "").strip(),
            description=str(item.get("comment") or "").strip(),
            price=price,
            currency=currency,
            rooms=parse_rooms(str(item.get("room") or "")),
            area=float(item.get("area") or 0),
            district=statement_district(item, code),
            city=code,
            url=self.base_url + path,
            photos=statement_photos(item),
            owner_name=str(item.get("user_title") or "").strip() or None,
            **statement_extras(item),
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
                    rooms=parse_rooms(_text(element, s.card_rooms)),
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
            statement = find_statement(data)
            if statement is not None:
                return statement_details(statement)
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
        if rooms := parse_rooms(_text(soup, s.detail_rooms)):
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
            if phone := clean_phone(raw_phone):
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


def _parse_area(text: str) -> float:
    """Площадь в м²: ``50 м²``, ``72.5 m²``."""
    match = re.search(r"(\d+(?:[.,]\d+)?)", text)
    return float(match.group(1).replace(",", ".")) if match else 0.0
