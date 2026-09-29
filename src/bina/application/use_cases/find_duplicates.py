"""Поиск одной и той же квартиры на разных сайтах (TASK-090)."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import structlog

from bina.application.duplicates import same_apartment
from bina.infrastructure.db.models import Listing

logger = structlog.get_logger(__name__)


class IDuplicatesRepository(Protocol):
    """Нужное для поиска дубликатов."""

    async def list_duplicates_unchecked(self, limit: int) -> list[Listing]: ...

    async def duplicate_candidates(self, listing: Listing) -> list[Listing]: ...

    async def mark_duplicate(self, listing_id: UUID, primary_id: UUID) -> None: ...

    async def mark_duplicates_checked(self, listing_ids: list[UUID]) -> None: ...


@dataclass(frozen=True, slots=True)
class DuplicateStats:
    """Итог поиска дубликатов."""

    checked: int
    found: int


class FindDuplicatesUseCase:
    """Помечает объявления, которые повторяют уже известную квартиру.

    Основное — объявление, появившееся раньше; новое становится его дубликатом и
    скрывается из поиска, пока основное в поиске. Не коммитит.
    """

    def __init__(self, listings: IDuplicatesRepository) -> None:
        self._listings = listings

    async def execute(self, limit: int) -> DuplicateStats:
        pending = await self._listings.list_duplicates_unchecked(limit)
        found = 0
        for listing in pending:
            if listing.duplicate_of is not None:
                continue
            for candidate in await self._listings.duplicate_candidates(listing):
                # Кандидат новее и сам ещё не проверен — он найдёт это объявление сам
                if (
                    candidate.created_at > listing.created_at
                    and candidate.duplicates_checked_at is None
                ):
                    continue
                if not same_apartment(listing, candidate):
                    continue
                primary_id = candidate.duplicate_of or candidate.id
                if primary_id == listing.id:
                    # Кандидат уже дубликат этого объявления
                    continue
                await self._listings.mark_duplicate(listing.id, primary_id)
                listing.duplicate_of = primary_id
                found += 1
                logger.info(
                    "Duplicate listing",
                    listing=f"{listing.source_name}:{listing.source_id}",
                    primary_id=str(primary_id),
                )
                break
        await self._listings.mark_duplicates_checked([listing.id for listing in pending])
        logger.info("Duplicates checked", checked=len(pending), found=found)
        return DuplicateStats(checked=len(pending), found=found)
