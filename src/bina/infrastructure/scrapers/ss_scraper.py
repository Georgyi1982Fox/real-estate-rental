import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import httpx
import structlog
from bs4 import BeautifulSoup

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.base_scraper import BaseWebsiteScraper
from bina.infrastructure.scrapers.nextjs import next_data, walk
from bina.infrastructure.scrapers.settings import SSSettings

logger = structlog.get_logger(__name__)

# После стольких ошибок страниц списка подряд парсинг останавливается
MAX_CONSECUTIVE_FAILURES = 3
SOURCE_NAME = "ss"
ROOMS_RE = re.compile(r"(\d+)\s*-?\s*(?:комнат|ოთახ|room)", re.IGNORECASE)


class SSScraper(BaseWebsiteScraper):
    """Парсер объявлений с SS.ge (home.ss.ge).

    Сайт на Next.js: объявления лежат JSON-ом в ``__NEXT_DATA__``
    (``props.pageProps.applicationList.realStateItemModel``) вместе с полным
    описанием, поэтому страницы объявлений не загружаются. Разбор HTML по
    селекторам остался запасным вариантом.
    """

    def __init__(
        self,
        base_url: str = SSSettings.BASE_URL,
        delay_seconds: int = 2,
        user_agents: list[str] | None = None,
        *,
        search_path: str = SSSettings.SEARCH_PATH,
        max_pages: int = SSSettings.MAX_PAGES,
        city_id: int | None = SSSettings.CITY_ID,
        dump_dir: Path | None = None,
    ) -> None:
        super().__init__(base_url, delay_seconds, user_agents)
        self.search_path = search_path
        self.max_pages = max_pages
        self.city_id = city_id
        self.dump_dir = dump_dir

    async def scrape_listings(self, limit: int) -> list[RawListing]:
        """Парсит до ``limit`` объявлений со страниц поиска."""
        logger.info("Starting SS scraping", limit=limit)
        listings: list[RawListing] = []
        seen: set[str] = set()
        failures = 0

        for page in range(1, self.max_pages + 1):
            if len(listings) >= limit:
                break
            url = self.base_url + self.search_path.format(page=page)
            try:
                html = await self._fetch_page(url)
            except httpx.HTTPError as exc:
                failures += 1
                logger.error("SS list page failed", page=page, error=str(exc))
                if failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error("Too many failed pages, stopping", failures=failures)
                    break
                continue
            failures = 0
            if page == 1:
                self._dump("ss_list.html", html)

            page_ids, page_listings = self._parse_page(html)
            if not page_ids - seen:
                # Пустая страница или сайт игнорирует номер страницы и отдаёт ту же
                logger.info("No more new listings on SS", page=page)
                break
            seen |= page_ids
            listings.extend(page_listings[: limit - len(listings)])

        logger.info("Finished SS scraping", total=len(listings))
        return listings

    def _dump(self, filename: str, html: str) -> None:
        """Сохраняет сырой HTML для сверки разбора с реальным сайтом."""
        if self.dump_dir is None:
            return
        self.dump_dir.mkdir(parents=True, exist_ok=True)
        path = self.dump_dir / filename
        path.write_text(html, encoding="utf-8")
        logger.info("Saved raw HTML", path=str(path))

    def _parse_listings(self, html: str) -> list[RawListing]:
        """Объявления нужного города со страницы поиска."""
        return self._parse_page(html)[1]

    def _parse_page(self, html: str) -> tuple[set[str], list[RawListing]]:
        """ID всех объявлений страницы и объявления нужного города.

        ID нужны отдельно: страница только с другими городами — не конец выдачи.
        """
        data = next_data(html)
        items = _applications(data) if data is not None else []
        if not items:
            listings = self._parse_listings_html(html)
            return {item.source_id for item in listings}, listings
        ids = {str(item["applicationId"]) for item in items}
        listings = [
            self._from_application(item)
            for item in items
            if self.city_id is None or (item.get("address") or {}).get("cityId") == self.city_id
        ]
        return ids, listings

    def _from_application(self, item: dict[str, Any]) -> RawListing:
        """Объявление из JSON-объекта сайта."""
        address = item.get("address") or {}
        price = item.get("price") or {}
        title = str(item.get("title") or "").strip()
        detail = str(item.get("detailUrl") or "")
        return RawListing(
            source_id=str(item["applicationId"]),
            source_name=SOURCE_NAME,
            title=title,
            description=str(item.get("description") or "").strip(),
            price=float(price.get("priceGeo") or 0),
            currency="GEL",
            rooms=_rooms(title, item.get("numberOfBedrooms")),
            area=float(item.get("totalArea") or 0),
            district=str(
                address.get("subdistrictTitle") or address.get("districtTitle") or "Unknown"
            ).strip(),
            url=f"{self.base_url}/ru/{quote('недвижимость/' + detail)}" if detail else "",
            photos=_photos(item.get("appImages")),
        )

    def _parse_listings_html(self, html: str) -> list[RawListing]:
        """Карточки со страницы поиска по CSS-селекторам (старая вёрстка)."""
        soup = BeautifulSoup(html, "lxml")
        listings: list[RawListing] = []

        # Находим все карточки объявлений
        listing_elements = soup.select(".estate-item")

        for element in listing_elements:
            try:
                # Получаем ID из URL
                link_elem = element.select_one(".title a")
                url = ""
                source_id = "unknown"
                if link_elem and link_elem.get("href"):
                    url = urljoin(self.base_url, str(link_elem.get("href")))
                    # Извлекаем ID из URL
                    id_match = re.search(r"/(\d+)", url)
                    if id_match:
                        source_id = id_match.group(1)

                # Заголовок
                title = link_elem.get_text(strip=True) if link_elem else "No title"

                # Цена
                price_elem = element.select_one(".price") or element.select_one(".value")
                price_text = price_elem.get_text(strip=True) if price_elem else "0 GEL"
                price, currency = self._parse_price(price_text)

                # Район
                district_elem = element.select_one(".location") or element.select_one(
                    ".address-line"
                )
                district = district_elem.get_text(strip=True) if district_elem else "Unknown"

                # Комнаты и площадь
                rooms = 1
                area = 0.0
                description_parts = []

                # Информация о комнатах
                room_info = element.select_one(".info-block:-soup-contains('კომნ')")
                if room_info:
                    room_text = room_info.get_text(strip=True)
                    room_match = re.search(r"(\d+)\s*კომ|(\d+)\s*комн", room_text, re.IGNORECASE)
                    if room_match:
                        rooms = int(room_match.group(1) or room_match.group(2))
                    description_parts.append(room_text)

                # Площадь
                area_info = element.select_one(".info-block:-soup-contains('მ²')")
                if area_info:
                    area_text = area_info.get_text(strip=True)
                    area_match = re.search(r"(\d+(?:\.\d+)?)", area_text)
                    if area_match:
                        area = float(area_match.group(1))
                    description_parts.append(area_text)

                # Дополнительное описание
                desc_elem = element.select_one(".description")
                if desc_elem:
                    description_parts.append(desc_elem.get_text(strip=True))

                description = (
                    " | ".join(description_parts) if description_parts else "No description"
                )

                # Фото
                photos = []
                img_elem = element.select_one("img")
                if img_elem and img_elem.get("src"):
                    # Убираем параметры размера из URL
                    img_src = str(img_elem.get("src")).split("?")[0]
                    photos.append(img_src)

                listing = RawListing(
                    source_id=source_id,
                    source_name="ss",
                    title=title,
                    description=description,
                    price=price,
                    currency=currency,
                    rooms=rooms,
                    area=area,
                    district=district,
                    url=url,
                    photos=photos,
                )
                listings.append(listing)

            except Exception as e:
                logger.warning("Error parsing SS listing", error=str(e))
                continue

        return listings

    def _parse_price(self, price_text: str) -> tuple[float, str]:
        """Парсит цену и валюту из текста."""
        # Удаляем лишние символы и пробелы
        price_text = price_text.replace(",", "").replace(" ", "")

        # Проверяем валюту
        if "$" in price_text or "USD" in price_text:
            currency = "USD"
            price_str = price_text.replace("$", "").replace("USD", "")
        elif "€" in price_text or "EUR" in price_text:
            currency = "EUR"
            price_str = price_text.replace("€", "").replace("EUR", "")
        elif "GEL" in price_text or "₾" in price_text:
            currency = "GEL"
            price_str = price_text.replace("GEL", "").replace("₾", "")
        else:
            currency = "GEL"
            price_str = price_text

        # Очищаем цену от нечисловых символов (кроме точки)
        price_clean = re.sub(r"[^\d.]", "", price_str)
        price = float(price_clean) if price_clean else 0.0

        return price, currency


def _applications(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Объявления из JSON страницы поиска (первый список объектов с ``applicationId``)."""
    for value in walk(data):
        if (
            isinstance(value, list)
            and value
            and all(isinstance(item, dict) and "applicationId" in item for item in value)
        ):
            return value
    return []


def _rooms(title: str, bedrooms: Any) -> int:
    """Комнаты из заголовка (``2-комнатная``), иначе спальни + гостиная."""
    match = ROOMS_RE.search(title)
    if match:
        return int(match.group(1))
    if isinstance(bedrooms, int) and bedrooms > 0:
        return bedrooms + 1
    return 1


def _photos(images: Any) -> list[str]:
    """Ссылки на фото, главное первым, по порядку сайта."""
    if not isinstance(images, list):
        return []
    ordered = sorted(
        (image for image in images if isinstance(image, dict)),
        key=lambda image: (not image.get("isMain"), image.get("orderNo") or 0),
    )
    photos: list[str] = []
    for image in ordered:
        url = str(image.get("fileName") or "")
        if url and url not in photos:
            photos.append(url)
    return photos
