"""Embeddings объявлений (TASK-012)."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bina.infrastructure.db.models import Embedding, Listing, ListingStatus


class EmbeddingsRepository:
    """Отпечатки объявлений: какие ещё не посчитаны и сохранение пачкой."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def to_embed(self, limit: int, model: str) -> list[Listing]:
        """Активные объявления без отпечатка этой модели, новые первыми."""
        has_embedding = (
            select(Embedding.id)
            .where(Embedding.listing_id == Listing.id, Embedding.model_name == model)
            .exists()
        )
        query = (
            select(Listing)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                ~has_embedding,
            )
            .options(selectinload(Listing.district))
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def save_many(self, vectors: Sequence[tuple[UUID, list[float]]], model: str) -> None:
        """Сохранить (или заменить) отпечатки; у объявления один отпечаток."""
        if not vectors:
            return
        statement = pg_insert(Embedding).values(
            [
                {"listing_id": listing_id, "vector": vector, "model_name": model}
                for listing_id, vector in vectors
            ]
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[Embedding.listing_id],
                set_={
                    "vector": statement.excluded.vector,
                    "model_name": statement.excluded.model_name,
                    "updated_at": func.now(),
                },
            )
        )

    async def save_embedding(self, listing_id: UUID, embedding: list[float]) -> None:
        """Сохранить отпечаток одного объявления (модель по умолчанию)."""
        await self.save_many([(listing_id, embedding)], "text-embedding-3-small")
