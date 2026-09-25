from typing import List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.models import Embedding


class EmbeddingsRepository:
    """Репозиторий для работы с embeddings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_embedding(self, listing_id: UUID, embedding: List[float]) -> None:
        """Сохраняет embedding для объявления."""
        # Проверяем, существует ли уже embedding
        query = select(Embedding).where(Embedding.listing_id == listing_id)
        result = await self._session.execute(query)
        existing_embedding = result.scalar_one_or_none()
        
        if existing_embedding is not None:
            # Обновляем существующий embedding
            existing_embedding.vector = embedding
        else:
            # Создаем новый embedding
            new_embedding = Embedding(
                listing_id=listing_id,
                vector=embedding,
            )
            self._session.add(new_embedding)