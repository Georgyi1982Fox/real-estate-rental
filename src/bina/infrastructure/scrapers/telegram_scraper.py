"""Объявления из публичных Telegram-каналов (TASK-091).

Веб-версия канала ``https://t.me/s/<канал>`` открывается без аккаунта: посты
лежат в HTML (текст, фото, дата). Пост — свободный текст, поэтому цену, район,
комнаты и площадь достаёт AI (:class:`IListingExtractor`). Разбираются только
новые посты: известные и уже отброшенные (продажа, «ищу») AI не
отправляются повторно (``needs_details``, ``bina_scrape_skips``).

Группы (не каналы) веб-версии не имеют — их так не прочитать.
"""

import dataclasses
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from bina.application.cities import DEFAULT_CITY, city_of
from bina.application.ports.listing_extractor import (
    ExtractedListing,
    IListingExtractor,
    ListingExtractionError,
)
from bina.application.ports.scraper import NeedsDetails, RawListing
from bina.application.rent_period import DAILY, MONTHLY
from bina.application.text import html_to_text
from bina.infrastructure.scrapers.base_scraper import KNOWN_PAGES_TO_STOP, BaseWebsiteScraper
from bina.infrastructure.scrapers.details import to_datetime
from bina.infrastructure.scrapers.settings import CITIES, TelegramSettings

logger = structlog.get_logger(__name__)

SOURCE_NAME = "telegram"
_BACKGROUND_URL_RE = re.compile(r"background-image:\s*url\(['\"]?([^'\")]+)['\"]?\)")
# Короче — не объявление (подпись к фото, реклама канала)
MIN_TEXT_CHARS = 40


@dataclass(frozen=True, slots=True)
class ChannelPost:
    """Пост канала."""

    channel: str
    post_id: int
    text: str
    photos: list[str]
    published_at: datetime | None


def parse_channel_page(html: str, channel: str) -> tuple[list[ChannelPost], int | None]:
    """Посты страницы (по порядку сайта: старые сверху) и ID для следующей, более старой."""
    soup = BeautifulSoup(html, "lxml")
    posts: list[ChannelPost] = []
    for message in soup.select(".tgme_widget_message[data-post]"):
        name, _, raw_id = str(message["data-post"]).rpartition("/")
        if not raw_id.isdigit() or name.lower() != channel.lower():
            # Репост из другого канала на этой странице — у него свой ID
            continue
        text_node = message.select_one(".tgme_widget_message_text")
        text = _post_text(text_node) if text_node is not None else ""
        times = message.select("time[datetime]")
        posts.append(
            ChannelPost(
                channel=name,
                post_id=int(raw_id),
                text=text,
                photos=_post_photos(message),
                published_at=to_datetime(times[-1]["datetime"]) if times else None,
            )
        )
    more = soup.select_one("a.tme_messages_more[data-before]")
    before = more.get("data-before") if more is not None else None
    return posts, int(str(before)) if before and str(before).isdigit() else None


def _post_text(node: Tag) -> str:
    """Текст поста с переносами строк (``<br>``), без эмодзи-картинок и лишних пробелов."""
    text = html_to_text(node.decode_contents())
    lines = [re.sub(r"[ \t\u00a0]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _post_photos(message: Tag) -> list[str]:
    photos: list[str] = []
    for wrap in message.select(".tgme_widget_message_photo_wrap"):
        match = _BACKGROUND_URL_RE.search(str(wrap.get("style") or ""))
        if match and match.group(1) not in photos:
            photos.append(match.group(1))
    return photos


def post_card(post: ChannelPost) -> RawListing:
    """Карточка поста до разбора AI: только текст, фото и дата (цена 0 — ещё неизвестна)."""
    return RawListing(
        source_id=f"{post.channel}/{post.post_id}",
        source_name=SOURCE_NAME,
        title="",
        description=post.text,
        price=0.0,
        currency="GEL",
        rooms=0,
        area=0.0,
        district="Unknown",
        url=f"https://t.me/{post.channel}/{post.post_id}",
        photos=post.photos,
        owner_name=f"@{post.channel}",
        published_at=post.published_at,
        # Дата поста — и «обновлено»: по ней сортировка «новые сверху»
        updated_at=post.published_at,
    )


def apply_extracted(
    card: RawListing, data: ExtractedListing, city: str, cities: tuple[str, ...] = ()
) -> RawListing:
    """Карточка с полями от AI; не аренда или не наш город — карточка без изменений.

    ``city`` — город канала (если AI город не назвал), ``cities`` — какие ещё города
    собираем (TASK-079: пост про Батуми в тбилисском канале).
    Без цены, комнат, площади или района объявление не сохранится (нормализатор
    его отбросит) и попадёт в пропущенные.
    """
    if not data.is_rental_offer:
        return card
    home = city_of(city) or DEFAULT_CITY
    code = city_of(data.city) if data.city is not None else home
    if code is None or (code != home and code not in cities):
        return card
    if None in (data.price, data.rooms, data.area) or not data.district:
        return card
    assert data.price is not None and data.rooms is not None and data.area is not None
    values: dict[str, Any] = {
        "title": data.title or card.title,
        "price": data.price,
        "currency": data.currency or "USD",
        "rooms": data.rooms,
        "area": data.area,
        "district": data.district,
        "floor": data.floor,
        "total_floors": data.total_floors,
        "bedrooms": data.bedrooms,
        "features": list(data.features),
        "address": data.address,
        "phone": data.phone,
        "has_details": True,
        "city": code,
        "rent_period": DAILY if data.daily else MONTHLY,
    }
    return dataclasses.replace(card, **values)


class TelegramChannelScraper(BaseWebsiteScraper):
    """Парсер публичных Telegram-каналов с объявлениями об аренде."""

    def __init__(
        self,
        extractor: IListingExtractor | None,
        channels: tuple[str, ...] = TelegramSettings.CHANNELS,
        base_url: str = TelegramSettings.BASE_URL,
        delay_seconds: int = 2,
        user_agents: list[str] | None = None,
        max_pages: int = TelegramSettings.MAX_PAGES,
        max_age_days: int = TelegramSettings.MAX_AGE_DAYS,
        city: str = TelegramSettings.CITY,
    ) -> None:
        super().__init__(base_url, delay_seconds, user_agents)
        self.extractor = extractor
        self.channels = channels
        self.max_pages = max_pages
        self.max_age = timedelta(days=max_age_days)
        self.city = city

    async def scrape_listings(
        self, limit: int, needs_details: NeedsDetails | None = None
    ) -> list[RawListing]:
        """Новые посты каналов (не старше ``max_age_days``), новые сверху."""
        logger.info("Starting Telegram scraping", channels=len(self.channels), limit=limit)
        cutoff = datetime.now(UTC) - self.max_age
        listings: list[RawListing] = []
        for channel in self.channels:
            if len(listings) >= limit:
                break
            await self._scrape_channel(channel, cutoff, listings, limit, needs_details)
        logger.info("Finished Telegram scraping", total=len(listings))
        return listings

    async def _scrape_channel(
        self,
        channel: str,
        cutoff: datetime,
        listings: list[RawListing],
        limit: int,
        needs_details: NeedsDetails | None,
    ) -> None:
        before: int | None = None
        known_pages = 0
        for _ in range(self.max_pages):
            if len(listings) >= limit:
                return
            url = f"{self.base_url}/s/{channel}" + (f"?before={before}" if before else "")
            try:
                html = await self._fetch_page(url)
            except httpx.HTTPError as exc:
                logger.error("Telegram channel page failed", channel=channel, error=str(exc))
                return
            posts, before = parse_channel_page(html, channel)
            recent = [
                post
                for post in posts
                if post.published_at is not None
                and post.published_at >= cutoff
                and len(post.text) >= MIN_TEXT_CHARS
            ]
            # Новые сверху: при лимите важнее свежие посты
            cards = [post_card(post) for post in reversed(recent)]
            fresh = await self._add_cards(cards, listings, limit, needs_details)
            known_pages = 0 if fresh or needs_details is None else known_pages + 1
            old_reached = any(
                post.published_at is not None and post.published_at < cutoff for post in posts
            )
            if before is None or not posts or old_reached or known_pages >= KNOWN_PAGES_TO_STOP:
                return

    async def close(self) -> None:
        """Закрывает HTTP-клиенты: свой и AI."""
        await super().close()
        close = getattr(self.extractor, "close", None)
        if close is not None:
            await close()

    async def with_details(self, card: RawListing, *, first: bool = False) -> RawListing:
        """Поля объявления из текста поста (AI)."""
        if self.extractor is None:
            return card
        try:
            data = await self.extractor.extract(card.description)
        except ListingExtractionError as exc:
            logger.warning("Telegram post not parsed", post=card.source_id, error=str(exc))
            return card
        return apply_extracted(card, data, self.city, CITIES)
