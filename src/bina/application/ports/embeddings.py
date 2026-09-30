"""Смысловые отпечатки текста — embeddings (TASK-012)."""

from collections.abc import Sequence
from typing import Protocol


class EmbeddingsError(Exception):
    """Сервис embeddings недоступен или ответил ошибкой."""


class IEmbedder(Protocol):
    # Модель: отпечатки разных моделей между собой не сравниваются
    model: str

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Вектор на каждый текст, в том же порядке.

        Raises:
            EmbeddingsError: сервис не ответил.
        """
        ...
