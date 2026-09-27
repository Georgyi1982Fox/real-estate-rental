from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawListing:
    """Сырое объявление из источника.

    ``language``: язык ``title``/``description`` (``ru`` или ``ka``); по нему
    текст попадает в ``title_ru``/``title_ka`` модели.
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


class BaseScraper(ABC):
    """Базовый класс парсера объявлений."""

    @abstractmethod
    async def scrape_listings(self, limit: int) -> list[RawListing]:
        """Парсит объявления из источника."""
