"""Порт AI-разбора объявления из свободного текста (TASK-091: Telegram-каналы)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ListingExtractionError(Exception):
    """AI не ответил или ответил не по формату (объявление попробуем в другой раз)."""


@dataclass(frozen=True, slots=True)
class ExtractedListing:
    """Что AI нашёл в тексте поста.

    ``is_rental_offer`` — долгосрочная аренда квартиры (не продажа, не посуточно,
    не «ищу квартиру», не реклама). Остальные поля — ``None``, если в тексте их нет.
    """

    is_rental_offer: bool
    city: str | None = None
    district: str | None = None
    price: float | None = None
    currency: str | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    area: float | None = None
    floor: int | None = None
    total_floors: int | None = None
    address: str | None = None
    phone: str | None = None
    # Коды удобств (bina.application.listing_details.FEATURES)
    features: list[str] = field(default_factory=list)
    # Короткий заголовок: «2-комн. квартира в Ваке, 60 м²» (на языке поста)
    title: str | None = None


class IListingExtractor(ABC):
    """Разбирает текст объявления."""

    @abstractmethod
    async def extract(self, text: str) -> ExtractedListing:
        """Поля из текста; :class:`ListingExtractionError` при сбое AI."""
