import dataclasses
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.base_scraper import BaseWebsiteScraper
from bina.infrastructure.scrapers.settings import MyHomeSelectors, MyHomeSettings

logger = structlog.get_logger(__name__)

SOURCE_NAME = "myhome"
# После стольких ошибок страниц списка подряд парсинг останавливается
MAX_CONSECUTIVE_FAILURES = 3


class MyHomeScraper(BaseWebsiteScraper):
    """Парсер объявлений с MyHome.ge.

    Два этапа: страницы списка (id, ссылка, краткие данные), затем страница
    каждого объявления (полное описание, все фото, телефон, имя арендодателя).
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

    async def scrape_listings(self, limit: int) -> list[RawListing]:
        """Парсит до ``limit`` объявлений (список + страницы объявлений)."""
        logger.info("Starting MyHome scraping", limit=limit, details=self.fetch_details)
        listings: list[RawListing] = []
        failures = 0

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
            for card in cards[: limit - len(listings)]:
                listings.append(await self._with_details(card, first=not listings))

        logger.info("Finished MyHome scraping", total=len(listings))
        return listings

    async def _with_details(self, card: RawListing, *, first: bool) -> RawListing:
        """Дополняет карточку данными со страницы объявления (при ошибке оставляет как есть)."""
        if not self.fetch_details or not card.url:
            return card
        try:
            html = await self._fetch_page(card.url)
        except httpx.HTTPError as exc:
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
        """Карточки со страницы списка."""
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

    def _parse_detail(self, html: str) -> dict[str, Any]:
        """Поля со страницы объявления; отсутствующие на странице не возвращаются."""
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
