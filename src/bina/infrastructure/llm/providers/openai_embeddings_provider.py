"""Embeddings через OpenAI-совместимый API (OpenAI, AITUNNEL и др.), TASK-012."""

from collections.abc import Sequence
from typing import Any

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from bina.application.ports.embeddings import EmbeddingsError
from bina.application.semantic_search import EMBEDDING_DIM
from bina.infrastructure.llm.providers.base_embeddings_provider import BaseEmbeddingsProvider

logger = structlog.get_logger(__name__)

DEFAULT_MODEL = "text-embedding-3-small"


class _RetryableError(Exception):
    """Сеть или 5xx/429: стоит повторить."""


class OpenAIEmbeddingsProvider(BaseEmbeddingsProvider):
    """``POST {base_url}/embeddings``: пачка текстов → пачка векторов по ``EMBEDDING_DIM``."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        """Ленивый инициализатор HTTP клиента."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Закрывает HTTP клиент."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Векторы для текстов (пустой список — без запроса).

        Raises:
            EmbeddingsError: сервис не ответил или ответил не тем.
        """
        if not texts:
            return []
        try:
            data = await self._request(list(texts))
        except (_RetryableError, httpx.HTTPError) as exc:
            raise EmbeddingsError(str(exc) or type(exc).__name__) from exc
        try:
            items = sorted(data["data"], key=lambda item: item["index"])
            vectors = [[float(value) for value in item["embedding"]] for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingsError("unexpected answer") from exc
        if len(vectors) != len(texts) or any(len(v) != EMBEDDING_DIM for v in vectors):
            raise EmbeddingsError(f"expected {len(texts)} vectors of {EMBEDDING_DIM} numbers")
        return vectors

    @retry(
        retry=retry_if_exception_type(_RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _request(self, texts: list[str]) -> dict[str, Any]:
        payload: dict[str, object] = {"model": self.model, "input": texts}
        # Модели text-embedding-3 умеют укорачивать вектор до размера колонки
        if self.model.startswith("text-embedding-3"):
            payload["dimensions"] = EMBEDDING_DIM
        try:
            response = await self.client.post(f"{self.base_url}/embeddings", json=payload)
        except httpx.RequestError as exc:
            raise _RetryableError(str(exc)) from exc
        if response.status_code == 429 or response.status_code >= 500:
            raise _RetryableError(f"HTTP {response.status_code}")
        if response.status_code >= 400:
            logger.error("Embeddings request rejected", status=response.status_code)
            raise EmbeddingsError(f"HTTP {response.status_code}: {response.text[:200]}")
        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise EmbeddingsError("answer is not JSON") from exc
        return data

    async def generate_embedding(self, text: str) -> list[float]:
        """Вектор одного текста."""
        return (await self.embed([text]))[0]
