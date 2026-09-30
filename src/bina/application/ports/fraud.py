"""Порт AI-проверки объявлений на мошенничество (TASK-011)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

from bina.application.ports.translator import ListingText

# Причины (коды): фронтенд и бот переводят их сами. Первые шесть ставит AI, остальные — правила
AI_REASONS: tuple[str, ...] = (
    "prepayment",  # просят предоплату/залог до просмотра, перевод на карту
    "off_platform",  # уводят в мессенджер/почту, «пишите только в WhatsApp»
    "urgency",  # давят сроком: «только сегодня», «много желающих»
    "too_good",  # слишком хорошо: элитное жильё почти даром
    "vague",  # нет адреса/деталей, шаблонный текст
    "owner_abroad",  # «хозяин за границей, ключи пришлём»
)
RULE_REASONS: tuple[str, ...] = (
    "price_far_below_market",  # цена за м² намного ниже средней по району
    "no_photos",
)
REASONS: frozenset[str] = frozenset(AI_REASONS + RULE_REASONS)


@dataclass(frozen=True, slots=True)
class ListingFacts:
    """Факты, которые AI видит вместе с текстом."""

    price: Decimal
    currency: str
    rooms: int
    area: Decimal
    district: str
    photos: int
    # Медиана цены за м² в районе (та же валюта и вид аренды); None — мало данных
    district_median_per_m2: Decimal | None = None
    # TASK-092: monthly — цена за месяц, daily — за сутки
    rent_period: str = "monthly"


@dataclass(frozen=True, slots=True)
class FraudVerdict:
    """Оценка AI: 0 — чисто, 100 — почти наверняка мошенник."""

    score: int
    reasons: list[str] = field(default_factory=list)


class FraudAnalysisError(Exception):
    """AI не смог дать корректную оценку."""


class IFraudAnalyzer(ABC):
    """Оценивает текст объявления на признаки мошенничества."""

    @abstractmethod
    async def analyze(self, text: ListingText, facts: ListingFacts) -> FraudVerdict:
        """Оценка объявления.

        Raises:
            FraudAnalysisError: если оценку получить не удалось.
        """
