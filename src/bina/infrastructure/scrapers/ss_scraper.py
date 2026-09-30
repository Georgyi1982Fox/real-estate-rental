import dataclasses
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import httpx
import structlog
from bs4 import BeautifulSoup

from bina.application.cities import DEFAULT_CITY, city_name, city_of
from bina.application.listing_details import clean_features
from bina.application.ports.scraper import NeedsDetails, RawListing
from bina.application.rent_period import DAILY, MONTHLY
from bina.infrastructure.scrapers.base_scraper import (
    KNOWN_PAGES_TO_STOP,
    BaseWebsiteScraper,
    ListingGoneError,
)
from bina.infrastructure.scrapers.details import (
    condition_code,
    join_address,
    to_datetime,
    to_float,
    to_int,
)
from bina.infrastructure.scrapers.nextjs import next_data, walk
from bina.infrastructure.scrapers.settings import CITIES, SSSettings

logger = structlog.get_logger(__name__)

# После стольких ошибок страниц списка подряд парсинг останавливается
MAX_CONSECUTIVE_FAILURES = 3
SOURCE_NAME = "ss"
# dealType посуточной аренды (RealEstateDealType-3 на сайте)
SS_DAILY_DEAL_TYPE = 3
ROOMS_RE = re.compile(r"(\d+)\s*-?\s*(?:комнат|ოთახ|room)", re.IGNORECASE)


class SSScraper(BaseWebsiteScraper):
    """Парсер объявлений с SS.ge (home.ss.ge).

    Сайт на Next.js: объявления лежат JSON-ом в ``__NEXT_DATA__``
    (``props.pageProps.applicationList.realStateItemModel``). В списке описание
    обрезано и нет удобств, телефона, санузлов, поэтому затем загружается
    страница каждого объявления (``props.pageProps.applicationData``, TASK-018).
    Разбор HTML по селекторам остался запасным вариантом.
    """

    def __init__(
        self,
        base_url: str = SSSettings.BASE_URL,
        delay_seconds: int = 2,
        user_agents: list[str] | None = None,
        *,
        search_path: str | None = None,
        daily_search_path: str | None = None,
        max_pages: int = SSSettings.MAX_PAGES,
        cities: tuple[str, ...] | None = CITIES,
        fetch_details: bool = True,
        dump_dir: Path | None = None,
    ) -> None:
        super().__init__(base_url, delay_seconds, user_agents)
        # Помесячная и посуточная аренда (TASK-092); свой адрес — без посуточной, если
        # её адрес не задан явно; пустой адрес посуточной — не собирать её
        if search_path is None:
            search_path = SSSettings.SEARCH_PATH
            if daily_search_path is None:
                daily_search_path = SSSettings.DAILY_SEARCH_PATH
        self.search_paths = [
            path for path in (search_path, daily_search_path) if path and path != "-"
        ]
        self.max_pages = max_pages
        # None — все города (без проверки)
        self.cities = cities
        self.fetch_details = fetch_details
        self.dump_dir = dump_dir

    async def scrape_listings(
        self, limit: int, needs_details: NeedsDetails | None = None
    ) -> list[RawListing]:
        """Парсит до ``limit`` объявлений со страниц поиска."""
        logger.info("Starting SS scraping", limit=limit)
        listings: list[RawListing] = []
        for path in self.search_paths:
            listings += await self._scrape_path(path, limit, needs_details)
        logger.info("Finished SS scraping", total=len(listings))
        return listings

    async def _scrape_path(
        self, search_path: str, limit: int, needs_details: NeedsDetails | None
    ) -> list[RawListing]:
        """Объявления одного раздела поиска (аренда или посуточная аренда)."""
        listings: list[RawListing] = []
        seen: set[str] = set()
        failures = known_pages = 0

        for page in range(1, self.max_pages + 1):
            if len(listings) >= limit:
                break
            url = self.base_url + search_path.format(page=page)
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
            if page == 1 and search_path == self.search_paths[0]:
                self._dump("ss_list.html", html)

            page_ids, page_listings = self._parse_page(html)
            if not page_ids - seen:
                # Пустая страница или сайт игнорирует номер страницы и отдаёт ту же
                logger.info("No more new listings on SS", page=page)
                break
            seen |= page_ids
            fresh = await self._add_cards(page_listings, listings, limit, needs_details)
            if page_listings:
                # Страница только с другими городами ничего не говорит о новизне
                known_pages = 0 if fresh or needs_details is None else known_pages + 1
            if known_pages >= KNOWN_PAGES_TO_STOP:
                logger.info("No new or changed listings on SS, stopping", page=page)
                break
        return listings

    async def with_details(self, card: RawListing, *, first: bool = False) -> RawListing:
        """Дополняет объявление данными его страницы (при ошибке оставляет как есть)."""
        if not self.fetch_details or not card.url:
            return card
        try:
            html = await self._fetch_page(card.url, expect=card.source_id)
        except (httpx.HTTPError, ListingGoneError) as exc:
            logger.warning("SS detail page failed", url=card.url, error=str(exc))
            return card
        if first:
            self._dump("ss_detail.html", html)
        details = self.details_from_html(html)
        if details is None:
            logger.warning("SS detail page not parsed", url=card.url)
            return card
        return dataclasses.replace(card, **details)

    def details_from_html(self, html: str) -> dict[str, Any] | None:
        """Поля ``RawListing`` со страницы объявления; None — страница не разобрана."""
        data = next_data(html)
        application = _application_data(data) if data is not None else None
        return application_details(application) if application is not None else None

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
        listings = []
        for item in items:
            address = item.get("address") or {}
            city = city_of(address.get("cityTitle"), ss_city_id=address.get("cityId"))
            if self.cities is None or city in self.cities:
                listings.append(self._from_application(item, city or DEFAULT_CITY))
        return ids, listings

    def _from_application(self, item: dict[str, Any], city: str = DEFAULT_CITY) -> RawListing:
        """Объявление из JSON-объекта сайта."""
        address = item.get("address") or {}
        price = item.get("price") or {}
        title = str(item.get("title") or "").strip()
        detail = str(item.get("detailUrl") or "")
        features = ["furniture"] if item.get("furniture") else []
        if item.get("withBuiltInKitchen"):
            features.append("kitchen_appliances")
        return RawListing(
            source_id=str(item["applicationId"]),
            source_name=SOURCE_NAME,
            title=title,
            description=str(item.get("description") or "").strip(),
            price=float(price.get("priceGeo") or 0),
            currency="GEL",
            rooms=_rooms(title, item.get("numberOfBedrooms")),
            area=float(item.get("totalArea") or 0),
            # Район не указан — объявление относится к городу в целом
            district=str(
                address.get("subdistrictTitle")
                or address.get("districtTitle")
                or city_name(city, "ru")
            ).strip(),
            city=city,
            url=f"{self.base_url}/ru/{quote('недвижимость/' + detail)}" if detail else "",
            photos=_photos(item.get("appImages")),
            floor=to_int(item.get("floorNumber")),
            total_floors=to_int(item.get("totalAmountOfFloor")),
            bedrooms=to_int(item.get("numberOfBedrooms")),
            features=features,
            address=join_address(address.get("streetTitle"), address.get("streetNumber")),
            published_at=to_datetime(item.get("createDate")),
            updated_at=to_datetime(item.get("orderDate")),
            rent_period=_rent_period(item.get("dealType")),
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

            except (AttributeError, IndexError, TypeError, ValueError) as e:
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


def _rent_period(deal_type: Any) -> str:
    """Вид аренды по ``dealType`` (``realEstateDealTypeId``): 3 — посуточная."""
    return DAILY if to_int(deal_type) == SS_DAILY_DEAL_TYPE else MONTHLY


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


# ----------------------------------------------------------- страница объявления

# Флаги удобств в applicationData → наши коды
_SS_FEATURES: dict[str, str] = {
    "furniture": "furniture",
    "withBuiltInKitchen": "kitchen_appliances",
    "airConditioning": "air_conditioning",
    "heating": "heating",
    "hotWater": "hot_water",
    "washingMachine": "washing_machine",
    "fridge": "fridge",
    "tv": "tv",
    "cableTelevision": "tv",
    "internet": "internet",
    "wiFi": "internet",
    "naturalGas": "gas",
    "elevator": "elevator",
    "garage": "parking",
    "balcony": "balcony",
    "storage": "storage",
    "withPool": "pool",
    "isPetFriendly": "pets_allowed",
    "securityAlarm": "security",
}
# ``applicationData.status`` снятого объявления (у активного — ``Active``)
_INACTIVE_STATUSES = {"inactive", "deleted", "expired", "blocked", "closed"}
# balcony_Loggia: «Нет в проекте», «Нет» — балкона нет; число или «Есть» — есть
_NO_BALCONY_RE = re.compile(r"^\s*(нет|no|არ)", re.IGNORECASE)


def _application_data(data: dict[str, Any]) -> dict[str, Any] | None:
    """``applicationData`` страницы объявления."""
    for value in walk(data):
        if isinstance(value, dict) and "applicationId" in value and "applicationPhones" in value:
            return value
    return None


def application_details(item: dict[str, Any]) -> dict[str, Any]:
    """Поля ``RawListing`` из ``applicationData`` (только найденные)."""
    details: dict[str, Any] = {"has_details": True}
    if item.get("realEstateDealTypeId") is not None:
        details["rent_period"] = _rent_period(item.get("realEstateDealTypeId"))
    status = str(item.get("status") or "")
    if item.get("isInactiveApplication") is True or status.lower() in _INACTIVE_STATUSES:
        details["active"] = False
    descriptions = item.get("description")
    if isinstance(descriptions, dict):
        texts = {
            code: str(descriptions.get(code) or "").strip()
            for code in ("ru", "ka", "en")
            if str(descriptions.get(code) or "").strip()
        }
        if texts.get("ru"):
            details["description"] = texts.pop("ru")
        details["descriptions"] = texts
    elif isinstance(descriptions, str) and descriptions.strip():
        details["description"] = descriptions.strip()

    phones = [p for p in item.get("applicationPhones") or [] if isinstance(p, dict)]
    phones.sort(key=lambda phone: not phone.get("isMain"))
    for phone in phones:
        number = re.sub(r"\D", "", str(phone.get("phoneNumber") or ""))
        if len(number) >= 6:
            details["phone"] = number
            break

    agency = item.get("agencyName") or item.get("companyName")
    if owner := str(agency or item.get("contactPerson") or "").strip():
        details["owner_name"] = owner
    entity = str(item.get("userEntityType") or "")
    if agency or item.get("agencyId") or item.get("companyId"):
        details["owner_type"] = "agent"
    elif entity.lower() == "individual":
        details["owner_type"] = "owner"
    elif entity:
        details["owner_type"] = "agent"

    for key, value in (
        ("floor", to_int(item.get("floor"))),
        ("total_floors", to_int(item.get("floors"))),
        ("bedrooms", to_int(item.get("bedrooms"))),
        ("bathrooms", to_int(item.get("toilet"))),
        ("rooms", to_int(item.get("rooms"))),
        ("area", to_float(item.get("totalArea"))),
        ("latitude", to_float(item.get("locationLatitude"))),
        ("longitude", to_float(item.get("locationLongitude"))),
        ("condition", condition_code(item.get("state"))),
        ("updated_at", to_datetime(item.get("orderDate"))),
    ):
        if value is not None:
            details[key] = value

    features = [code for key, code in _SS_FEATURES.items() if item.get(key) is True]
    balcony = item.get("balcony_Loggia")
    if isinstance(balcony, str) and balcony.strip() and not _NO_BALCONY_RE.match(balcony):
        features.append("balcony")
    details["features"] = clean_features(features)

    address = item.get("address") or {}
    if street := join_address(address.get("streetTitle"), address.get("streetNumber")):
        details["address"] = street
    if photos := _photos(item.get("appImages")):
        details["photos"] = photos
    return details
