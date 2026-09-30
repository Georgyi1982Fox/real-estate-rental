"""Фото собственников на диске (TASK-024, TASK-025).

Пока бот работает на компьютере владельца, фото лежат в папке ``MEDIA_DIR``
(в Docker — том ``media``), а API отдаёт их по адресу ``/api/media/...``.
Перед сохранением фото уменьшается до ``MAX_SIDE`` по большей стороне и
пересохраняется в JPEG: так оно быстро открывается в Telegram и весит мало,
а заодно проверяется, что это действительно картинка.
"""

import io
import os
import uuid
from pathlib import Path

import structlog
from PIL import Image, ImageOps, UnidentifiedImageError

from bina.application.ports.photo_storage import PhotoError

logger = structlog.get_logger(__name__)

MEDIA_URL = "/api/media"
MAX_SIDE = 1600
JPEG_QUALITY = 85
# Больше не принимаем (телефоны снимают до ~10 МБ)
MAX_PHOTO_BYTES = 15 * 1024 * 1024
# Защита от «картинок-бомб»: не больше 50 мегапикселей
Image.MAX_IMAGE_PIXELS = 50_000_000


def media_dir() -> Path:
    """Папка с фото: ``MEDIA_DIR`` или ``./media``."""
    return Path(os.getenv("MEDIA_DIR") or "media")


def optimize(data: bytes) -> bytes:
    """JPEG не больше MAX_SIDE по большей стороне, с учётом поворота из EXIF."""
    if not data or len(data) > MAX_PHOTO_BYTES:
        raise PhotoError("photo is empty or too large")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            fixed = ImageOps.exif_transpose(image)
            fixed = fixed.convert("RGB")
            fixed.thumbnail((MAX_SIDE, MAX_SIDE))
            out = io.BytesIO()
            # EXIF (в том числе координаты съёмки) не сохраняем
            fixed.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise PhotoError(str(exc)) from exc
    return out.getvalue()


class LocalPhotoStorage:
    """Фото в папке на диске: ``<root>/listings/<folder>/<id>.jpg``."""

    def __init__(self, root: Path | None = None, url_prefix: str = MEDIA_URL) -> None:
        self.root = root or media_dir()
        self.url_prefix = url_prefix.rstrip("/")

    def save(self, folder: str, data: bytes) -> str:
        jpeg = optimize(data)
        name = f"{uuid.uuid4().hex}.jpg"
        path = self.root / "listings" / _safe(folder) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(jpeg)
        logger.info("Photo saved", path=str(path), size=len(jpeg))
        return f"{self.url_prefix}/listings/{_safe(folder)}/{name}"

    def delete(self, url: str) -> None:
        prefix = f"{self.url_prefix}/"
        if not url.startswith(prefix):
            return
        path = (self.root / url[len(prefix) :]).resolve()
        if self.root.resolve() in path.parents:
            path.unlink(missing_ok=True)


def _safe(folder: str) -> str:
    """Имя папки без «..» и разделителей (ID объявления)."""
    cleaned = "".join(char for char in folder if char.isalnum() or char in "-_")
    if not cleaned:
        raise ValueError("empty folder name")
    return cleaned
