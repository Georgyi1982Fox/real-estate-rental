"""Фото Telegram сохраняются у нас, а не остаются на временных ссылках (TASK-091)."""

import io
from pathlib import Path
from uuid import uuid4

from PIL import Image

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.photo_mirror import TelegramPhotoMirror
from bina.infrastructure.storage.photos import LocalPhotoStorage


def _png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(out, "PNG")
    return out.getvalue()


def _mirror(tmp_path: Path, downloads: dict[str, bytes | None]) -> TelegramPhotoMirror:
    async def download(url: str) -> bytes | None:
        return downloads.get(url)

    storage = LocalPhotoStorage(root=tmp_path, url_prefix="/api/media")
    return TelegramPhotoMirror(storage, download)


def _card(photos: list[str], source_name: str = "telegram") -> RawListing:
    return RawListing(
        source_id="chan/1",
        source_name=source_name,
        title="",
        description="Сдаётся квартира",
        price=500,
        currency="USD",
        rooms=2,
        area=50.0,
        district="Ваке",
        url="https://t.me/chan/1",
        photos=photos,
    )


async def test_remote_photos_saved_locally(tmp_path: Path) -> None:
    remote = "https://cdn4.telesco.pe/file/a.jpg"
    mirror = _mirror(tmp_path, {remote: _png()})

    [card] = await mirror.mirror_listings([_card([remote])])

    assert len(card.photos) == 1
    url = card.photos[0]
    assert url.startswith("/api/media/listings/")
    # Файл действительно сохранён на диске
    assert (tmp_path / url[len("/api/media/") :]).is_file()


async def test_failed_download_keeps_original(tmp_path: Path) -> None:
    remote = "https://cdn4.telesco.pe/file/gone.jpg"
    mirror = _mirror(tmp_path, {remote: None})

    [card] = await mirror.mirror_listings([_card([remote])])

    assert card.photos == [remote]


async def test_local_urls_not_downloaded_again(tmp_path: Path) -> None:
    called: list[str] = []

    async def download(url: str) -> bytes | None:
        called.append(url)
        return _png()

    mirror = TelegramPhotoMirror(LocalPhotoStorage(root=tmp_path), download)
    local = "/api/media/listings/chan1/x.jpg"

    [card] = await mirror.mirror_listings([_card([local])])

    assert card.photos == [local]
    assert called == []


async def test_non_telegram_listing_untouched(tmp_path: Path) -> None:
    remote = "https://ss.ge/photo.jpg"
    mirror = _mirror(tmp_path, {remote: _png()})

    [card] = await mirror.mirror_listings([_card([remote], source_name="ss")])

    assert card.photos == [remote]


class _StoredListing:
    def __init__(self, images: list[str]) -> None:
        self.id = uuid4()
        self.images = images


async def test_backfill_replaces_remote_images(tmp_path: Path) -> None:
    remote = "https://cdn4.telesco.pe/file/b.jpg"
    local = "/api/media/listings/old/keep.jpg"
    mirror = _mirror(tmp_path, {remote: _png()})
    listing = _StoredListing([local, remote])

    fixed = await mirror.backfill([listing])  # type: ignore[list-item]

    assert fixed == 1
    assert listing.images[0] == local
    assert listing.images[1].startswith("/api/media/listings/")


async def test_backfill_skips_all_local(tmp_path: Path) -> None:
    mirror = _mirror(tmp_path, {})
    listing = _StoredListing(["/api/media/listings/old/a.jpg"])

    fixed = await mirror.backfill([listing])  # type: ignore[list-item]

    assert fixed == 0
