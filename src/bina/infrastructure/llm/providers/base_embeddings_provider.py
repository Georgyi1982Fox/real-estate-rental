from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger(__name__)


class BaseEmbeddingsProvider(ABC):
    """Базовый класс для провайдеров embeddings."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> list[float]:
        """Генерирует embedding для текста."""
        pass
