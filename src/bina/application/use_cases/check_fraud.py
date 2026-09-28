"""Проверка новых объявлений на мошенничество (TASK-011).

Для каждого непроверенного объявления: правила (цена против медианы района,
фото) + оценка AI по тексту → итоговый балл и причины. Ошибка AI на одном
объявлении не останавливает остальные: оно останется непроверенным до
следующего запуска.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import structlog

from bina.application.fraud import HIDE_SCORE, WARNING_SCORE, combine, rule_signals
from bina.application.ports.fraud import FraudAnalysisError, IFraudAnalyzer, ListingFacts
from bina.application.repositories.fraud import IFraudRepository
from bina.application.use_cases.translate_listings import listing_text, source_language
from bina.infrastructure.db.models import Listing

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class FraudStats:
    """Итог запуска."""

    checked: int
    suspicious: int  # предупреждение (WARNING_SCORE и выше, но ниже HIDE_SCORE)
    hidden: int  # HIDE_SCORE и выше
    failed: int


class CheckFraudUseCase:
    """Проверяет до ``limit`` объявлений за запуск."""

    def __init__(
        self,
        analyzer: IFraudAnalyzer,
        repository: IFraudRepository,
        after_save: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """``after_save`` вызывается после каждой сохранённой оценки (обычно commit)."""
        self._analyzer = analyzer
        self._repository = repository
        self._after_save = after_save
        self._medians: dict[tuple[UUID, str], Decimal | None] = {}

    async def execute(self, limit: int) -> FraudStats:
        """Сам не коммитит: транзакцией управляет вызывающий код (см. ``after_save``)."""
        listings = await self._repository.list_fraud_unchecked(limit)
        checked = suspicious = hidden = failed = 0
        for listing in listings:
            facts = await self._facts(listing)
            source = source_language(listing) or "ru"
            try:
                ai = await self._analyzer.analyze(listing_text(listing, source), facts)
            except FraudAnalysisError as exc:
                failed += 1
                logger.warning("Fraud check failed", listing_id=str(listing.id), error=str(exc))
                continue
            verdict = combine(ai, rule_signals(facts))
            await self._repository.save_fraud(listing.id, verdict.score, verdict.reasons)
            if self._after_save is not None:
                await self._after_save()
            checked += 1
            if verdict.score >= HIDE_SCORE:
                hidden += 1
            elif verdict.score >= WARNING_SCORE:
                suspicious += 1
            if verdict.score >= WARNING_SCORE:
                logger.info(
                    "Suspicious listing",
                    listing_id=str(listing.id),
                    score=verdict.score,
                    reasons=verdict.reasons,
                )

        stats = FraudStats(checked=checked, suspicious=suspicious, hidden=hidden, failed=failed)
        logger.info(
            "Fraud check finished",
            checked=checked,
            suspicious=suspicious,
            hidden=hidden,
            failed=failed,
        )
        return stats

    async def _facts(self, listing: Listing) -> ListingFacts:
        key = (listing.district_id, listing.currency)
        if key not in self._medians:
            self._medians[key] = await self._repository.district_median_per_m2(*key)
        district = listing.district
        return ListingFacts(
            price=Decimal(listing.price),
            currency=listing.currency,
            rooms=listing.rooms,
            area=Decimal(listing.area),
            district=(district.name_en or district.name_ru) if district is not None else "",
            photos=len(listing.images or []),
            district_median_per_m2=self._medians[key],
        )
