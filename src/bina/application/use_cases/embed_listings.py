"""Отпечатки смысла (embeddings) для новых объявлений (TASK-012)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import structlog

from bina.application.ports.embeddings import EmbeddingsError, IEmbedder
from bina.application.semantic_search import listing_text
from bina.infrastructure.db.models import Listing

logger = structlog.get_logger(__name__)

# Текстов в одном запросе к сервису
BATCH_SIZE = 32


class IEmbeddingsRepository(Protocol):
    async def to_embed(self, limit: int, model: str) -> list[Listing]: ...

    async def save_many(self, vectors: Sequence[tuple[UUID, list[float]]], model: str) -> None: ...


@dataclass(frozen=True, slots=True)
class EmbedStats:
    checked: int
    embedded: int
    failed: int


class EmbedListingsUseCase:
    """Считает отпечатки пачками. Не коммитит (``after_batch`` — коммит после пачки)."""

    def __init__(
        self,
        repository: IEmbeddingsRepository,
        embedder: IEmbedder,
        batch_size: int = BATCH_SIZE,
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._batch_size = batch_size

    async def execute(self, limit: int) -> EmbedStats:
        """До ``limit`` объявлений. Сервис не ответил — остальные в следующий раз.

        Raises:
            EmbeddingsError: первая же пачка не посчиталась (ключ, модель, сеть):
                шаг расписания отметит сбой, владелец получит сообщение.
        """
        listings = await self._repository.to_embed(limit, self._embedder.model)
        embedded = failed = 0
        for start in range(0, len(listings), self._batch_size):
            batch = listings[start : start + self._batch_size]
            try:
                vectors = await self._embedder.embed([listing_text(item) for item in batch])
            except EmbeddingsError:
                if embedded == 0:
                    raise
                failed += len(listings) - start
                logger.warning("Embeddings failed, rest next time", left=failed)
                break
            await self._repository.save_many(
                [(item.id, vector) for item, vector in zip(batch, vectors, strict=True)],
                self._embedder.model,
            )
            embedded += len(batch)
        return EmbedStats(checked=len(listings), embedded=embedded, failed=failed)
