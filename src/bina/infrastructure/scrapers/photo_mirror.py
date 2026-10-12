"""Фото из Telegram — у нас на диске (TASK-091).

Фото в постах Telegram отдаются по временным ссылкам ``cdn*.telesco.pe``, которые
со временем перестают открываться — и картинки у объявлений из каналов пропадают.
Поэтому фото скачиваются и сохраняются в ``MEDIA_DIR`` (как фото собственников,
см. :mod:`bina.infrastructure.storage.photos`), а в объявлении остаётся постоянный
адрес ``/api/media/...``.

Применяется только к объявлениям Telegram: у сайтов свои постоянные адреса фото.
"""

import dataclasses
from collections.abc import Awaitable, Callable

import httpx
import structlog

from bina.application.ports.photo_storage import PhotoError
from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import Listing
from bina.infrastructure.scrapers.telegram_scraper import SOURCE_NAME as TELEGRAM
from bina.infrastructure.storage.photos import MEDIA_URL, LocalPhotoStorage

logger = structlog.get_logger(__name__)

# Больше фото с одного поста не сохраняем (на объявлении их всё равно столько не нужно)
MAX_PHOTOS = 10

# Скачиватель фото: адрес → байты (``None`` — скачать не вышло)
Download = Callable[[str], Awaitable[bytes | None]]


def http_download(client: httpx.AsyncClient) -> Download:
    """Скачиватель фото на основе готового HTTP-клиента парсера."""

    async def download(url: str) -> bytes | None:
        try:
            response = await client.get(url, timeout=30, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Telegram photo download failed", url=url, error=str(exc))
            return None
        return response.content

    return download


class TelegramPhotoMirror:
    """Скачивает фото постов и сохраняет их у нас; адрес становится ``/api/media/...``."""

    def __init__(
        self, storage: LocalPhotoStorage, download: Download, *, media_url: str = MEDIA_URL
    ) -> None:
        self._storage = storage
        self._download = download
        self._local_prefix = media_url.rstrip("/") + "/"

    def _is_local(self, url: str) -> bool:
        return url.startswith(self._local_prefix)

    async def _mirror_one(self, folder: str, url: str) -> str:
        """Один адрес фото → наш, если удалось скачать и сохранить; иначе прежний."""
        if self._is_local(url):
            return url
        data = await self._download(url)
        if not data:
            return url
        try:
            return self._storage.save(folder, data)
        except PhotoError as exc:
            logger.warning("Telegram photo not saved", url=url, error=str(exc))
            return url

    async def mirror_urls(self, folder: str, urls: list[str]) -> list[str]:
        """Список адресов фото → наши адреса (повторы убираются, порядок сохраняется)."""
        return [await self._mirror_one(folder, url) for url in dict.fromkeys(urls)]

    async def mirror_listings(self, listings: list[RawListing]) -> list[RawListing]:
        """Заменить ссылки на фото у новых и изменившихся объявлений Telegram."""
        result: list[RawListing] = []
        for item in listings:
            if item.source_name == TELEGRAM and item.photos:
                photos = await self.mirror_urls(item.source_id, list(item.photos)[:MAX_PHOTOS])
                result.append(dataclasses.replace(item, photos=photos))
            else:
                result.append(item)
        return result

    async def backfill(self, listings: list[Listing]) -> int:
        """Перескачать фото уже сохранённых объявлений; вернуть число исправленных."""
        fixed = 0
        for listing in listings:
            images = list(listing.images or [])
            if not images or all(self._is_local(url) for url in images):
                continue
            mirrored = await self.mirror_urls(listing.id.hex, images)
            if mirrored != images:
                listing.images = mirrored
                fixed += 1
        return fixed
