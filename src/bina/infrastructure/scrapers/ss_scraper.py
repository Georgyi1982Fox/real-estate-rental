import re
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup

from src.bina.application.ports.scraper import RawListing
from src.bina.infrastructure.scrapers.base_scraper import BaseWebsiteScraper

logger = structlog.get_logger(__name__)


class SSScraper(BaseWebsiteScraper):
    """Парсер объявлений с SS.ge."""

    def __init__(
        self,
        base_url: str = "https://ss.ge",
        delay_seconds: int = 2,
        user_agents: list[str] | None = None,
    ) -> None:
        super().__init__(base_url, delay_seconds, user_agents)

    async def scrape_listings(self, limit: int) -> list[RawListing]:
        """Парсит объявления с SS.ge."""
        logger.info("Starting SS scraping", limit=limit)

        listings: list[RawListing] = []
        page = 1

        while len(listings) < limit:
            # Формируем URL для аренды жилья в Тбилиси
            url = f"{self.base_url}/ru/le/ixiris-nawlebis-teqebi/tebilisi?Page={page}"

            try:
                html = await self._fetch_page(url)
                page_listings = self._parse_listings(html)

                if not page_listings:
                    logger.info("No more listings found on SS")
                    break

                # Добавляем объявления до достижения лимита
                remaining = limit - len(listings)
                listings.extend(page_listings[:remaining])

                logger.debug("Parsed listings from page", page=page, count=len(page_listings), total=len(listings))
                page += 1

            except Exception as e:
                logger.error("Error scraping SS page", page=page, error=str(e))
                break

        logger.info("Finished SS scraping", total_scraped=len(listings))
        return listings

    def _parse_listings(self, html: str) -> list[RawListing]:
        """Парсит объявления со страницы HTML."""
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
                    url = urljoin(self.base_url, link_elem.get("href"))
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
                district_elem = element.select_one(".location") or element.select_one(".address-line")
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

                description = " | ".join(description_parts) if description_parts else "No description"

                # Фото
                photos = []
                img_elem = element.select_one("img")
                if img_elem and img_elem.get("src"):
                    # Убираем параметры размера из URL
                    img_src = img_elem.get("src").split("?")[0]
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
