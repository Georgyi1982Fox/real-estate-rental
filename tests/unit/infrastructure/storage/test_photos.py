"""Фото собственников на диске (TASK-096)."""

import io
from pathlib import Path

import pytest
from PIL import Image

from bina.application.ports.photo_storage import PhotoError
from bina.infrastructure.storage.photos import MAX_SIDE, LocalPhotoStorage, optimize


def png(width: int, height: int) -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", (width, height), (200, 100, 50, 255)).save(out, "PNG")
    return out.getvalue()


def test_optimize_resizes_to_jpeg() -> None:
    with Image.open(io.BytesIO(optimize(png(4000, 3000)))) as result:
        assert result.format == "JPEG"
        assert result.size == (MAX_SIDE, 1200)
    with Image.open(io.BytesIO(optimize(png(800, 600)))) as small:
        assert small.size == (800, 600), "маленькое фото не увеличивается"


@pytest.mark.parametrize("data", [b"", b"not an image", b"\x89PNG broken"])
def test_optimize_rejects_junk(data: bytes) -> None:
    with pytest.raises(PhotoError):
        optimize(data)


def test_save_and_delete(tmp_path: Path) -> None:
    storage = LocalPhotoStorage(tmp_path)
    url = storage.save("abc123", png(100, 100))

    assert url.startswith("/api/media/listings/abc123/") and url.endswith(".jpg")
    path = tmp_path / url.removeprefix("/api/media/")
    assert path.is_file()

    storage.delete("/api/media/../../etc/passwd")
    storage.delete("https://elsewhere/photo.jpg")
    storage.delete(url)
    assert not path.exists()


def test_folder_name_is_sanitized(tmp_path: Path) -> None:
    url = LocalPhotoStorage(tmp_path).save("../../evil", png(10, 10))
    assert url.startswith("/api/media/listings/evil/")
    with pytest.raises(ValueError, match="empty"):
        LocalPhotoStorage(tmp_path).save("../..", png(10, 10))
