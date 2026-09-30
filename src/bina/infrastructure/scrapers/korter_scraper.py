"""Парсер объявлений Korter.ge (TASK-092).

Страницы Korter.ge приходят с данными внутри: JSON в
``window.INITIAL_STATE = {...}``. На странице раздела аренды города —
``apartmentListingStore.apartments`` (по 20 объявлений: цена, комнаты, площадь,
район, дом с точкой на карте, первое фото); на странице объявления —
``layoutLandingStore`` (описание, все фото, спальни, санузлы, продавец и его
телефон).

Собирается помесячная (``section: rent``) и посуточная (``daily_rent``) аренда
квартир Тбилиси и Батуми.
"""

import dataclasses
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import structlog

from bina.application.cities import city_name
from bina.application.ports.scraper import NeedsDetails, RawListing
from bina.application.rent_period import DAILY, MONTHLY
from bina.infrastructure.scrapers.base_scraper import (
    KNOWN_PAGES_TO_STOP,
    BaseWebsiteScraper,
    ListingGoneError,
)
from bina.infrastructure.scrapers.details import to_datetime, to_float, to_int
from bina.infrastructure.scrapers.settings import CITIES, KorterSettings

logger = structlog.get_logger(__name__)

SOURCE_NAME = "korter"
# После стольких ошибок страниц списка подряд парсинг города останавливается
MAX_CONSECUTIVE_FAILURES = 3
STATE_RE = re.compile(r"window\.INITIAL_STATE\s*=\s*")
# ``section`` объявления → вид аренды; продажа и прочее не берутся
SECTIONS = {"rent": MONTHLY, "daily_rent": DAILY}
# Типы продавца, которые — не собственник
AGENT_SELLERS = {"realtor", "agency", "developer", "company"}


class KorterScraper(BaseWebsiteScraper):
    """Объявления об аренде квартир с Korter.ge."""

    def __init__(
        self,
        base_url: str = KorterSettings.BASE_URL,
        delay_seconds: int = 2,
        user_agents: list[str] | None = None,
        *,
        search_paths: dict[str, str] | None = None,
        daily_search_paths: dict[str, str] | None = None,
        cities: tuple[str, ...] = CITIES,
        max_pages: int = KorterSettings.MAX_PAGES,
        fetch_details: bool = True,
        dump_dir: Path | None = None,
    ) -> None:
        super().__init__(base_url, delay_seconds, user_agents)
        explicit = search_paths is not None
        paths = search_paths if search_paths is not None else KorterSettings.SEARCH_PATHS
        daily = daily_search_paths
        if daily is None:
            # Свои адреса разделов (тесты, ручной запуск) — без посуточной, если не задана
            daily = {} if explicit else KorterSettings.DAILY_SEARCH_PATHS
        # Город и адрес раздела: сначала помесячная аренда, затем посуточная
        self.searches = [
            (city, path)
            for source in (paths, daily)
            for city, path in source.items()
            if city in cities
        ]
        self.max_pages = max_pages
        self.fetch_details = fetch_details
        self.dump_dir = dump_dir

    async def scrape_listings(
        self, limit: int, needs_details: NeedsDetails | None = None
    ) -> list[RawListing]:
        """До ``limit`` объявлений каждого раздела (город, вид аренды)."""
        logger.info("Starting Korter scraping", limit=limit)
        listings: list[RawListing] = []
        for city, path in self.searches:
            listings += await self._scrape_section(city, path, limit, needs_details)
        logger.info("Finished Korter scraping", total=len(listings))
        return listings

    async def _scrape_section(
        self, city: str, search_path: str, limit: int, needs_details: NeedsDetails | None
    ) -> list[RawListing]:
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
                logger.error("Korter list page failed", page=page, error=str(exc))
                if failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error("Too many failed pages, stopping", failures=failures)
                    break
                continue
            failures = 0
            if page == 1 and not listings:
                self._dump(f"korter_list_{city}.html", html)

            cards = self.parse_list(html, city)
            ids = {card.source_id for card in cards}
            if not ids - seen:
                # Пусто или сайт отдал ту же страницу (страниц меньше, чем мы просим)
                logger.info("No more listings on Korter", page=page, city=city)
                break
            seen |= ids
            fresh = await self._add_cards(cards, listings, limit, needs_details)
            known_pages = 0 if fresh or needs_details is None else known_pages + 1
            if known_pages >= KNOWN_PAGES_TO_STOP:
                logger.info("No new or changed listings on Korter, stopping", page=page, city=city)
                break
        return listings

    def parse_list(self, html: str, city: str) -> list[RawListing]:
        """Объявления об аренде квартир со страницы раздела."""
        state = initial_state(html)
        store = state.get("apartmentListingStore") if state else None
        items = store.get("apartments") if isinstance(store, dict) else None
        if not isinstance(items, list):
            return []
        cards = [self.card(item, city) for item in items if isinstance(item, dict)]
        return [card for card in cards if card is not None]

    def card(self, item: dict[str, Any], city: str) -> RawListing | None:
        """Объявление из элемента списка; не аренда квартиры — ``None``."""
        period = SECTIONS.get(str(item.get("section") or ""))
        object_id = item.get("objectId")
        if period is None or object_id is None or item.get("propertyCategory") != "flat":
            return None
        building = _dict(item.get("building"))
        position = _dict(building.get("position"))
        house = _dict(item.get("house"))
        floors = item.get("floorNumbers")
        district = str(item.get("subLocalityNominative") or "").strip()
        rooms = _rooms(item.get("roomCount"))
        link = str(item.get("link") or "")
        return RawListing(
            source_id=str(object_id),
            source_name=SOURCE_NAME,
            title=_title(item, district),
            description="",
            price=float(item.get("price") or 0),
            currency=str(item.get("currency") or "GEL").upper(),
            rooms=rooms,
            area=float(item.get("area") or 0),
            # Район не указан — объявление относится к городу в целом
            district=district or city_name(city, "ru"),
            city=city,
            url=self.base_url + quote(link, safe="/-") if link else "",
            photos=_list_photo(item),
            floor=to_int(floors[0]) if isinstance(floors, list) and floors else None,
            total_floors=to_int(house.get("floorCount")),
            address=str(item.get("address") or "").strip() or None,
            latitude=to_float(position.get("lat")),
            longitude=to_float(position.get("lng")),
            updated_at=to_datetime(item.get("actualizeTime")),
            rent_period=period,
        )

    async def with_details(self, card: RawListing, *, first: bool = False) -> RawListing:
        """Дополняет объявление данными его страницы (при ошибке оставляет как есть)."""
        if not self.fetch_details or not card.url:
            return card
        try:
            html = await self._fetch_page(card.url, expect=card.source_id)
        except (httpx.HTTPError, ListingGoneError) as exc:
            logger.warning("Korter detail page failed", url=card.url, error=str(exc))
            return card
        if first:
            self._dump("korter_detail.html", html)
        details = self.details_from_html(html)
        if details is None:
            logger.warning("Korter detail page not parsed", url=card.url)
            return card
        return dataclasses.replace(card, **details)

    def details_from_html(self, html: str) -> dict[str, Any] | None:
        """Поля ``RawListing`` со страницы объявления; None — страница не разобрана."""
        state = initial_state(html)
        store = state.get("layoutLandingStore") if state else None
        layout = store.get("layout") if isinstance(store, dict) else None
        if not isinstance(store, dict) or not isinstance(layout, dict):
            return None
        return layout_details(layout, store.get("seller"))

    def _dump(self, filename: str, html: str) -> None:
        """Сохраняет сырой HTML для сверки разбора с реальным сайтом."""
        if self.dump_dir is None:
            return
        self.dump_dir.mkdir(parents=True, exist_ok=True)
        path = self.dump_dir / filename
        path.write_text(html, encoding="utf-8")
        logger.info("Saved raw HTML", path=str(path))


def initial_state(html: str) -> dict[str, Any] | None:
    """JSON из ``window.INITIAL_STATE = {...}`` (``None``, если его нет или он битый)."""
    match = STATE_RE.search(html)
    if match is None:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html, match.end())
    except json.JSONDecodeError:
        logger.warning("Korter INITIAL_STATE is not valid JSON")
        return None
    return data if isinstance(data, dict) else None


def layout_details(layout: dict[str, Any], seller: Any) -> dict[str, Any]:
    """Подробности объявления со страницы (только найденные)."""
    details: dict[str, Any] = {"has_details": True}
    if isinstance(description := layout.get("description"), str) and description.strip():
        details["description"] = description.strip()
    if photos := _layout_photos(layout.get("images")):
        details["photos"] = photos
    for key, value in (
        ("bedrooms", to_int(layout.get("bedroomCount"))),
        ("bathrooms", to_int(layout.get("bathroomCount"))),
        ("published_at", to_datetime(layout.get("publishTime") or layout.get("createTime"))),
        ("updated_at", to_datetime(layout.get("actualizeTime"))),
    ):
        if value is not None:
            details[key] = value
    if rooms := _rooms(layout.get("roomCount")):
        details["rooms"] = rooms
    if layout.get("hasBalcony") or layout.get("hasTerrace"):
        details["features"] = ["balcony"]
    status = str(layout.get("publicationStatus") or "published")
    if layout.get("available") == "no" or status not in {"published", ""}:
        # Сдано или снято с публикации
        details["active"] = False
    if isinstance(seller, dict):
        if name := str(seller.get("name") or "").strip():
            details["owner_name"] = name
        seller_type = str(seller.get("sellerType") or "").lower()
        if seller_type:
            details["owner_type"] = "agent" if seller_type in AGENT_SELLERS else "owner"
        if phone := _seller_phone(seller.get("phones")):
            details["phone"] = phone
    return details


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _title(item: dict[str, Any], district: str) -> str:
    """«3-комнатная квартира, Крцаниси» (заголовков у объявлений Korter нет)."""
    label = str(item.get("propertyTypeRoomCountLabel") or "Квартира").strip()
    return f"{label}, {district}" if district else label


def _rooms(value: Any) -> int:
    """Комнаты; студия (0 комнат) — одна комната."""
    rooms = to_int(value)
    return max(rooms or 0, 1) if rooms is not None else 0


def _list_photo(item: dict[str, Any]) -> list[str]:
    """Фото из списка (одно, крупное)."""
    media = item.get("mediaSrc")
    default = media.get("default") if isinstance(media, dict) else None
    if not isinstance(default, dict):
        return []
    url = str(default.get("x2") or default.get("x1") or "")
    return [url] if url else []


def _layout_photos(images: Any) -> list[str]:
    """Все фото со страницы объявления, по порядку сайта."""
    if not isinstance(images, list):
        return []
    photos: list[str] = []
    for image in images:
        media = image.get("mediaSrc") if isinstance(image, dict) else None
        default = media.get("default") if isinstance(media, dict) else None
        url = str(default.get("x1") or default.get("x2") or "") if isinstance(default, dict) else ""
        if url and url not in photos:
            photos.append(url)
    return photos


def _seller_phone(phones: Any) -> str | None:
    """Основной номер продавца: ``+995 568 51 55 36`` → ``+995568515536``."""
    if not isinstance(phones, list):
        return None
    ordered = sorted(
        (phone for phone in phones if isinstance(phone, dict)),
        key=lambda phone: not phone.get("isMain"),
    )
    for phone in ordered:
        number = re.sub(r"[^\d+]", "", str(phone.get("displayNumber") or ""))
        if len(re.sub(r"\D", "", number)) >= 6:
            return number
    return None
