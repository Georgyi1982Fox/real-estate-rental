from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class RawListing:
    """Сырое объявление из источника."""
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
    photos: List[str]


class BaseScraper(ABC):
    """Базовый класс парсера объявлений."""

    @abstractmethod
    async def scrape_listings(self, limit: int) -> List[RawListing]:
        """Парсит объявления из источника."""
        pass