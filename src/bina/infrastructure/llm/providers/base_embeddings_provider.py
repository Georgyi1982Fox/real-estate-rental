from abc import ABC, abstractmethod
from typing import List

import structlog

logger = structlog.get_logger(__name__)


class BaseEmbeddingsProvider(ABC):
    """Базовый класс для провайдеров embeddings."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Генерирует embedding для текста."""
        pass