import re
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup

from src.bina.application.ports.scraper import RawListing
from src.bina.infrastructure.scrapers.base_scraper import BaseWebsiteScraper

logger = structlog.get_logger(__name__)


class MyHomeScraper(BaseWebsiteScraper):
    """Парсер объявлений с MyHome.ge."""

    def __init__(
        self,
        base_url: str = "https://www.myhome.ge",
        delay_seconds: int = 2,
        user_agents: list[str] | None = None,
    ) -> None:
        super().__init__(base_url, delay_seconds, user_agents)

    async def scrape_listings(self, limit: int) -> list[RawListing]:
        """Парсит объявления с MyHome.ge."""
        logger.info("Starting MyHome scraping", limit=limit)

        listings: list[RawListing] = []
        page = 1

        while len(listings) < limit:
            # Формируем URL для аренды жилья в Тбилиси
            url = f"{self.base_url}/ru/search?AjaxSearchFieldForm%5Bpr_type%5D=1&AjaxSearchFieldForm%5Blist_type%5D=2&AjaxSearchFieldForm%5Bcity_id%5D=1&AjaxSearchFieldForm%5Bcurrency%5D=1&page={page}"

            try:
                html = await self._fetch_page(url)
                page_listings = self._parse_listings(html)

                if not page_listings:
                    logger.info("No more listings found on MyHome")
                    break

                # Добавляем объявления до достижения лимита
                remaining = limit - len(listings)
                listings.extend(page_listings[:remaining])

                logger.debug("Parsed listings from page", page=page, count=len(page_listings), total=len(listings))
                page += 1

            except Exception as e:
                logger.error("Error scraping MyHome page", page=page, error=str(e))
                break

        logger.info("Finished MyHome scraping", total_scraped=len(listings))
        return listings

    def _parse_listings(self, html: str) -> list[RawListing]:
        """Парсит объявления со страницы HTML."""
        soup = BeautifulSoup(html, "lxml")
        listings: list[RawListing] = []

        # Находим все карточки объявлений
        # Используем более общий селектор, так как структура может меняться
        listing_elements = soup.select("[data-listing-id]")

        for element in listing_elements:
            try:
                listing_id = element.get("data-listing-id")
                if not listing_id:
                    continue

                # Получаем базовую информацию
                title_elem = element.select_one(".card-title a")
                title = title_elem.get_text(strip=True) if title_elem else "No title"

                url = ""
                if title_elem and title_elem.get("href"):
                    url = urljoin(self.base_url, title_elem.get("href"))

                # Цена
                price_elem = element.select_one(".price-tag")
                price_text = price_elem.get_text(strip=True) if price_elem else "0 GEL"
                price, currency = self._parse_price(price_text)

                # Район
                district_elem = element.select_one(".location") or element.select_one(".card-location")
                district = district_elem.get_text(strip=True) if district_elem else "Unknown"

                # Комнаты и площадь из описания
                rooms = 1
                area = 0.0
                description_parts = []

                # Пытаемся найти комнаты и площадь в различных местах
                room_elem = element.select_one(".info-item.-rooms") or element.select_one(".card-rooms")
                if room_elem:
                    room_text = room_elem.get_text(strip=True)
                    room_match = re.search(r"(\d+)\s*к|(\d+)\s*комн", room_text, re.IGNORECASE)
                    if room_match:
                        rooms = int(room_match.group(1) or room_match.group(2))
                    description_parts.append(room_text)

                area_elem = element.select_one(".info-item.-area") or element.select_one(".card-area")
                if area_elem:
                    area_text = area_elem.get_text(strip=True)
                    area_match = re.search(r"(\d+(?:\.\d+)?)", area_text)
                    if area_match:
                        area = float(area_match.group(1))
                    description_parts.append(area_text)

                # Дополнительное описание
                desc_elem = element.select_one(".description") or element.select_one(".card-description")
                if desc_elem:
                    description_parts.append(desc_elem.get_text(strip=True))

                description = " | ".join(description_parts) if description_parts else "No description"

                # Фото
                photos = []
                img_elem = element.select_one("img")
                if img_elem and img_elem.get("src"):
                    photos.append(img_elem.get("src"))
                elif img_elem and img_elem.get("data-src"):
                    photos.append(img_elem.get("data-src"))

                listing = RawListing(
                    source_id=listing_id,
                    source_name="myhome",
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
                logger.warning("Error parsing MyHome listing", error=str(e))
                continue

        return listings

    def _parse_price(self, price_text: str) -> tuple[float, str]:
        """Парсит цену и валюту из текста."""
        # Удаляем лишние символы и пробелы
        price_text = price_text.replace(",", "").replace(" ", "")

        # Проверяем валюту
        if "USD" in price_text:
            currency = "USD"
            price_str = price_text.replace("USD", "")
        elif "EUR" in price_text:
            currency = "EUR"
            price_str = price_text.replace("EUR", "")
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
