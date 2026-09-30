"""Порт хранилища фото объявлений собственников (TASK-096)."""

from typing import Protocol


class PhotoError(Exception):
    """Файл — не фото (или слишком большой)."""


class IPhotoStorage(Protocol):
    """Сохраняет фото и отдаёт ссылку, по которой его видно в боте и Mini App."""

    def save(self, folder: str, data: bytes) -> str:
        """Сохранить фото объявления ``folder``; вернуть ссылку. :class:`PhotoError` — не фото."""
        ...

    def delete(self, url: str) -> None:
        """Удалить фото по ссылке (нет такого — ничего не делать)."""
        ...
