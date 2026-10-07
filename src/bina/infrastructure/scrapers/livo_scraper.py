"""Парсер объявлений Livo.ge (TASK-092).

Livo.ge — сайт TNET (как MyHome.ge), но объявления на нём в основном свои.
Список объявлений — со страницы поиска сайта (``livo.ge/ru/s?...&page=N``): с октября
2026 API списка (``/v1/statements``) без входа отвечает 401, а сервер сайта кладёт те же
объявления прямо в страницу (данные Next.js ``self.__next_f.push``). Объявление целиком —
из API сайта (``api-statements.tnet.ge/v1/statements/{id}``, ключ в заголовке
``X-Website-Key``). Формат объявления — как у MyHome.ge
(:mod:`bina.infrastructure.scrapers.tnet`).

Собирается помесячная и посуточная аренда квартир Тбилиси и Батуми.
"""

import dataclasses
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import structlog

from bina.application.cities import CITIES as CITY_INFO
from bina.application.cities import DEFAULT_CITY
from bina.application.ports.scraper import NeedsDetails, RawListing
from bina.infrastructure.scrapers.base_scraper import (
    KNOWN_PAGES_TO_STOP,
    BaseWebsiteScraper,
    ListingGoneError,
)
from bina.infrastructure.scrapers.settings import CITIES, LivoSettings
from bina.infrastructure.scrapers.tnet import (
    statement_city,
    statement_details,
    statement_district,
    statement_extras,
    statement_photos,
    statement_price,
    statement_rooms,
)

logger = structlog.get_logger(__name__)

SOURCE_NAME = "livo"
# После стольких ошибок страниц списка подряд парсинг останавливается
MAX_CONSECUTIVE_FAILURES = 3
# Платные объявления (VIP) стоят в начале выдачи вне порядка дат: по ним не судим,
# есть ли дальше новые
PROMOTED_FLAGS = ("is_super_vip", "is_vip_plus", "is_vip")
# ID объявления в конце адреса страницы: ``/udzravi-qoneba/qiravdeba-bina/...-26187474``
PAGE_ID_RE = re.compile(r"-(\d+)/?$")


def _drop_cities_filter(query: str) -> str:
    """Убрать из запроса фильтр по городу (``cities=...``): берём все города Грузии."""
    parts = [part for part in query.split("&") if not part.startswith("cities=")]
    return "&".join(parts)


class LivoScraper(BaseWebsiteScraper):
    """Объявления Livo.ge из API сайта: список, затем объявление целиком."""

    def __init__(
        self,
        base_url: str = LivoSettings.BASE_URL,
        delay_seconds: int = 2,
        user_agents: list[str] | None = None,
        *,
        api_url: str = LivoSettings.API_URL,
        website_key: str = LivoSettings.WEBSITE_KEY,
        search_query: str = LivoSettings.SEARCH_QUERY,
        cities: tuple[str, ...] = CITIES,
        max_pages: int = LivoSettings.MAX_PAGES,
        fetch_details: bool = True,
        dump_dir: Path | None = None,
    ) -> None:
        super().__init__(base_url, delay_seconds, user_agents)
        self.api_url = api_url.rstrip("/")
        # Русский: заголовки и районы на том же языке, что у MyHome.ge
        self.headers = {"X-Website-Key": website_key, "locale": "ru", "Accept": "application/json"}
        self.cities = cities
        # Номер города есть не у всех: если выбран хоть один без номера или выбраны все
        # города, фильтр по городу в запросе убираем — берём всю Грузию и отсеиваем лишнее
        # уже у себя (``scrape_listings``). Иначе фильтруем на стороне API (меньше трафика).
        ids = {code: CITY_INFO[code].tnet_city_id for code in cities if code in CITY_INFO}
        all_known = ids and all(value is not None for value in ids.values())
        if all_known and set(cities) != set(CITY_INFO):
            city_ids = ",".join(str(value) for value in ids.values())
            self.search_query = search_query.replace("{cities}", city_ids)
        else:
            self.search_query = _drop_cities_filter(search_query)
        self.max_pages = max_pages
        self.fetch_details = fetch_details
        self.dump_dir = dump_dir

    async def scrape_listings(
        self, limit: int, needs_details: NeedsDetails | None = None
    ) -> list[RawListing]:
        """До ``limit`` объявлений со страниц выдачи API (новые сверху)."""
        logger.info("Starting Livo scraping", limit=limit)
        listings: list[RawListing] = []
        failures = known_pages = 0

        for page in range(1, self.max_pages + 1):
            if len(listings) >= limit:
                break
            # Русская версия страницы: заголовки и районы по-русски, как у MyHome.ge
            url = f"{self.base_url}/ru/s?{self.search_query.format(page=page)}"
            try:
                body = await self._fetch_page(url)
            except httpx.HTTPError as exc:
                failures += 1
                logger.error("Livo list page failed", page=page, error=str(exc))
                if failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error("Too many failed pages, stopping", failures=failures)
                    break
                continue
            failures = 0
            if page == 1:
                self._dump("livo_list.html", body)

            items = list_items(body)
            if not items:
                logger.info("No more listings on Livo", page=page)
                break
            promoted = [self.card(item) for item in items if _promoted(item)]
            regular = [self.card(item) for item in items if not _promoted(item)]
            await self._add_cards(self._wanted(promoted), listings, limit, needs_details)
            wanted = self._wanted(regular)
            fresh = await self._add_cards(wanted, listings, limit, needs_details)
            if wanted:
                known_pages = 0 if fresh or needs_details is None else known_pages + 1
            if known_pages >= KNOWN_PAGES_TO_STOP:
                logger.info("No new or changed listings on Livo, stopping", page=page)
                break

        logger.info("Finished Livo scraping", total=len(listings))
        return listings

    def _wanted(self, cards: list[RawListing]) -> list[RawListing]:
        """Объявления нужных городов (API фильтрует сам, это на всякий случай)."""
        return [card for card in cards if card.city in self.cities]

    def card(self, item: dict[str, Any]) -> RawListing:
        """Объявление из элемента списка API."""
        price, currency = statement_price(item)
        listing_id = str(item["id"])
        city = statement_city(item, DEFAULT_CITY)
        return RawListing(
            source_id=listing_id,
            source_name=SOURCE_NAME,
            title=str(item.get("dynamic_title") or "").strip(),
            description=str(item.get("comment") or "").strip(),
            price=price,
            currency=currency,
            rooms=statement_rooms(item),
            area=float(item.get("area") or 0),
            district=statement_district(item, city),
            city=city,
            url=self.page_url(item),
            photos=statement_photos(item),
            owner_name=str(item.get("user_title") or "").strip() or None,
            **statement_extras(item),
        )

    def page_url(self, item: dict[str, Any]) -> str:
        """Страница объявления на сайте (как её строит сам Livo.ge)."""
        middle = str(item.get("middle_slug") or "qiravdeba-bina")
        slug = str(item.get("dynamic_slug") or "bina")
        return f"{self.base_url}/udzravi-qoneba/{quote(middle)}/{quote(slug)}-{item['id']}"

    def detail_url(self, listing_id: str) -> str:
        return f"{self.api_url}/v1/statements/{listing_id}"

    # tenacity ≥ 9.2 типизирует родительский метод как обёртку @retry
    async def _fetch_page(  # type: ignore[override, unused-ignore]
        self, url: str, expect: str | None = None
    ) -> str:
        """Страницу объявления (перепроверка, TASK-018) читаем через API: у сайта нет HTML."""
        if url.startswith(self.base_url) and (match := PAGE_ID_RE.search(url)):
            url = self.detail_url(match.group(1))
        return await super()._fetch_page(url)

    async def with_details(self, card: RawListing, *, first: bool = False) -> RawListing:
        """Дополняет объявление полными данными (при ошибке оставляет как есть)."""
        if not self.fetch_details:
            return card
        try:
            body = await self._fetch_page(self.detail_url(card.source_id))
        except (httpx.HTTPError, ListingGoneError) as exc:
            logger.warning("Livo listing failed", source_id=card.source_id, error=str(exc))
            return card
        if first:
            self._dump("livo_detail.json", body)
        details = self.details_from_html(body)
        if details is None:
            logger.warning("Livo listing not parsed", source_id=card.source_id)
            return card
        return dataclasses.replace(card, **details)

    def details_from_html(self, html: str) -> dict[str, Any] | None:
        """Поля ``RawListing`` из ответа API об объявлении; None — ответ не разобран."""
        statement = detail_statement(html)
        return statement_details(statement) if statement is not None else None

    def _dump(self, filename: str, body: str) -> None:
        """Сохраняет сырой ответ для сверки разбора с реальным сайтом."""
        if self.dump_dir is None:
            return
        self.dump_dir.mkdir(parents=True, exist_ok=True)
        path = self.dump_dir / filename
        path.write_text(body, encoding="utf-8")
        logger.info("Saved raw response", path=str(path))


def _json(body: str) -> Any:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Livo response is not JSON")
        return None


def list_items(body: str) -> list[dict[str, Any]]:
    """Объявления страницы поиска сайта или ответа API ``/v1/statements`` (``data.data``)."""
    if not body.lstrip().startswith("{"):
        return page_statements(body)
    data = _json(body)
    page = data.get("data") if isinstance(data, dict) else None
    items = page.get("data") if isinstance(page, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict) and "id" in item]


# Куски данных Next.js в странице: self.__next_f.push([1,"<строка JSON>"])
_FLIGHT_RE = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
_DEAL_TYPE_RE = re.compile(r'"deal_type_id"')
# Сколько скобок «{» назад пробовать, ища начало объявления вокруг поля
_MAX_BRACES_BACK = 300


def page_statements(html: str) -> list[dict[str, Any]]:
    """Объявления из данных Next.js в странице поиска (по порядку, без повторов).

    Объявление — объект с ``id`` и ``deal_type_id`` (тот же формат, что у API). Для каждого
    поля ``deal_type_id`` берётся ближайший объект вокруг него — порядок ключей и
    переводы строк в описаниях разбору не мешают.
    """
    try:
        text = "".join(json.loads(f'"{chunk}"') for chunk in _FLIGHT_RE.findall(html))
    except json.JSONDecodeError:
        logger.warning("Livo page data is broken")
        return []
    decoder = json.JSONDecoder(strict=False)
    found: dict[Any, dict[str, Any]] = {}
    for match in _DEAL_TYPE_RE.finditer(text):
        position = match.start()
        for _ in range(_MAX_BRACES_BACK):
            position = text.rfind("{", 0, position)
            if position < 0:
                break
            try:
                item, end = decoder.raw_decode(text, position)
            except json.JSONDecodeError:
                continue
            if end > match.start() and isinstance(item, dict) and "deal_type_id" in item:
                if "id" in item:
                    found.setdefault(item["id"], item)
                break
    return list(found.values())


def detail_statement(body: str) -> dict[str, Any] | None:
    """Объявление из ответа ``/v1/statements/{id}`` (``data.statement``)."""
    data = _json(body)
    page = data.get("data") if isinstance(data, dict) else None
    statement = page.get("statement") if isinstance(page, dict) else None
    return statement if isinstance(statement, dict) and "id" in statement else None


def _promoted(item: dict[str, Any]) -> bool:
    return any(item.get(flag) for flag in PROMOTED_FLAGS)
