"""Игрушечные embeddings для тестов умного поиска: по ключевым словам."""

from collections.abc import Sequence

from bina.application.ports.embeddings import EmbeddingsError
from bina.application.semantic_search import EMBEDDING_DIM

# Группы синонимов на трёх языках: одна группа — одна ось вектора
GROUPS: tuple[tuple[str, ...], ...] = (
    ("balcony", "балкон", "აივან"),
    ("metro", "метро", "მეტრო"),
    ("pets", "животн", "cat", "кот"),
    ("sea", "море", "ზღვ"),
)


def keyword_vector(text: str) -> list[float]:
    lowered = text.lower()
    vector = [0.0] * EMBEDDING_DIM
    for axis, group in enumerate(GROUPS):
        if any(word in lowered for word in group):
            vector[axis] = 1.0
    # Ненулевой «фон», чтобы косинус был определён и у текстов без ключевых слов
    vector[EMBEDDING_DIM - 1] = 0.1
    return vector


def similarity(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class FakeEmbedder:
    model = "fake-embeddings"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[list[str]] = []

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        if self.fail:
            raise EmbeddingsError("service down")
        return [keyword_vector(text) for text in texts]
