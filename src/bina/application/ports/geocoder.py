"""Поиск точки на карте по адресу (TASK-080)."""

from typing import Protocol


class GeocoderError(Exception):
    """Сервис карт недоступен или ответил ошибкой (попробуем в следующий раз)."""


class IGeocoder(Protocol):
    async def locate(self, address: str, city: str) -> tuple[float, float] | None:
        """(широта, долгота) или ``None``, если адрес не найден."""
        ...
