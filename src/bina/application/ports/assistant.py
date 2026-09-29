"""Порт AI-помощника арендатора (TASK-095, Premium)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class AssistantError(Exception):
    """AI не ответил или ответил не по формату."""


@dataclass(frozen=True, slots=True)
class ListingBrief:
    """Что AI знает об объявлении."""

    title: str
    description: str
    price: str
    rooms: int
    area: float
    district: str
    floor: int | None = None
    total_floors: int | None = None
    address: str | None = None
    features: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OwnerMessage:
    """Сообщение хозяину на грузинском и его перевод для пользователя."""

    text_ka: str
    translation: str


class IAssistant(ABC):
    """AI-помощник."""

    @abstractmethod
    async def message_owner(self, listing: ListingBrief, language: str, note: str) -> OwnerMessage:
        """Вежливое сообщение хозяину на грузинском (+ перевод на ``language``)."""

    @abstractmethod
    async def viewing_questions(self, listing: ListingBrief, language: str, note: str) -> list[str]:
        """5-8 вопросов для просмотра именно этой квартиры, на ``language``."""
