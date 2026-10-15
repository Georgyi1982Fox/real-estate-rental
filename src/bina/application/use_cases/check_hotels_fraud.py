"""Проверка гостиниц на мошенничество (TASK-120, этап 2).

Как у квартир (:mod:`check_fraud`), но факты — гостиничные (тип, звёзды, цена за ночь,
вместимость, удобства, фото), а не цена за м² против медианы района. AI смотрит описание
на те же признаки обмана. Ошибка AI на одной гостинице не останавливает остальные.
"""

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import structlog

from bina.application.fraud import HIDE_SCORE, WARNING_SCORE
from bina.application.ports.fraud import (
    FraudAnalysisError,
    FraudVerdict,
    HotelFacts,
    IHotelFraudAnalyzer,
)
from bina.application.ports.translator import ListingText
from bina.application.use_cases.check_fraud import FraudStats
from bina.application.use_cases.translate_hotels import description_language, hotel_description
from bina.infrastructure.db.models import Hotel

logger = structlog.get_logger(__name__)


class IHotelFraudRepository(Protocol):
    """Непроверенные гостиницы и сохранение оценки."""

    async def list_fraud_unchecked(self, limit: int) -> list[Hotel]: ...
    async def save_fraud(self, hotel_id: UUID, score: int, reasons: list[str]) -> None: ...


def hotel_facts(hotel: Hotel) -> HotelFacts:
    return HotelFacts(
        kind=hotel.kind,
        city=hotel.city,
        price_per_night_gel=Decimal(hotel.min_price_gel) if hotel.min_price_gel else None,
        max_guests=hotel.max_guests or 0,
        stars=hotel.stars,
        amenities=len(hotel.amenities or []),
        photos=len(hotel.images or []),
    )


def hotel_text(hotel: Hotel) -> ListingText:
    language = description_language(hotel) or "en"
    return ListingText(title=hotel.name, description=hotel_description(hotel, language))


class CheckHotelsFraudUseCase:
    """Проверяет до ``limit`` гостиниц за запуск."""

    def __init__(
        self,
        analyzer: IHotelFraudAnalyzer,
        repository: IHotelFraudRepository,
        after_save: Callable[[], Awaitable[None]] | None = None,
        concurrency: int = 1,
    ) -> None:
        self._analyzer = analyzer
        self._repository = repository
        self._after_save = after_save
        self._concurrency = max(1, concurrency)

    async def execute(self, limit: int) -> FraudStats:
        """Сам не коммитит: транзакцией управляет вызывающий код (см. ``after_save``)."""
        hotels = await self._repository.list_fraud_unchecked(limit)
        checked = suspicious = hidden = failed = 0
        semaphore = asyncio.Semaphore(self._concurrency)

        async def run(hotel: Hotel) -> tuple[Hotel, FraudVerdict | FraudAnalysisError]:
            async with semaphore:
                try:
                    text, facts = hotel_text(hotel), hotel_facts(hotel)
                    return hotel, await self._analyzer.analyze_hotel(text, facts)
                except FraudAnalysisError as exc:
                    return hotel, exc

        for finished in asyncio.as_completed([run(hotel) for hotel in hotels]):
            hotel, verdict = await finished
            if isinstance(verdict, FraudAnalysisError):
                failed += 1
                logger.warning("Hotel fraud failed", hotel_id=str(hotel.id), error=str(verdict))
                continue
            await self._repository.save_fraud(hotel.id, verdict.score, verdict.reasons)
            if self._after_save is not None:
                await self._after_save()
            checked += 1
            if verdict.score >= HIDE_SCORE:
                hidden += 1
            elif verdict.score >= WARNING_SCORE:
                suspicious += 1
            if verdict.score >= WARNING_SCORE:
                logger.info(
                    "Suspicious hotel",
                    hotel_id=str(hotel.id),
                    score=verdict.score,
                    reasons=verdict.reasons,
                )

        logger.info(
            "Hotel fraud check finished",
            checked=checked,
            suspicious=suspicious,
            hidden=hidden,
            failed=failed,
        )
        return FraudStats(checked=checked, suspicious=suspicious, hidden=hidden, failed=failed)
