from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawListing:
    """Сырое объявление из источника.

    ``language``: язык ``title``/``description`` (``ru`` или ``ka``); по нему
    текст попадает в ``title_ru``/``title_ka`` модели.

    Поля после ``language`` — подробности со страницы объявления (TASK-018);
    ``None`` — источник их не дал.
    """

    source_id: str
    source_name: str
    title: str
    description: str
    price: float
    currency: str
    rooms: int
    area: float
    district: str
    url: str
    photos: list[str] = field(default_factory=list)
    phone: str | None = None
    owner_name: str | None = None
    language: str = "ru"
    # Описания на других языках, если источник их даёт сам (SS.ge: ka/en/ru)
    descriptions: dict[str, str] = field(default_factory=dict)
    floor: int | None = None
    total_floors: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    # Коды удобств (bina.application.listing_details.FEATURES) и состояния (CONDITIONS)
    features: list[str] = field(default_factory=list)
    condition: str | None = None
    # owner — собственник, agent — агентство/риелтор (OWNER_TYPES)
    owner_type: str | None = None
    # Улица и дом как на сайте (на языке источника)
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    # Даты на сайте-источнике: публикация и последнее обновление/поднятие
    published_at: datetime | None = None
    updated_at: datetime | None = None
    # Загружена ли страница объявления (иначе — только краткие данные из списка)
    has_details: bool = False
    # False — страница объявления говорит, что оно снято (сдано, удалено)
    active: bool = True


# Нужно ли открывать страницу объявления (False — оно уже есть в базе и не менялось)
NeedsDetails = Callable[[RawListing], Awaitable[bool]]


class BaseScraper(ABC):
    """Базовый класс парсера объявлений."""

    @abstractmethod
    async def scrape_listings(
        self, limit: int, needs_details: NeedsDetails | None = None
    ) -> list[RawListing]:
        """Парсит объявления из источника.

        ``needs_details`` решает, открывать ли страницу объявления; без него —
        открывать все.
        """
