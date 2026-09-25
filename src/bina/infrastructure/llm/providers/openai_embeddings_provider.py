from typing import List

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from bina.infrastructure.llm.providers.base_embeddings_provider import BaseEmbeddingsProvider

logger = structlog.get_logger(__name__)


class OpenAIEmbeddingsProvider(BaseEmbeddingsProvider):
    """Провайдер embeddings для OpenAI."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-ada-002",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """Генерирует embedding для текста."""
        logger.debug("Generating embedding", text_length=len(text))
        
        try:
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                json={
                    "model": self.model,
                    "input": text,
                },
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]
            logger.debug("Generated embedding successfully", embedding_length=len(embedding))
            return embedding

        except httpx.HTTPStatusError as e:
            logger.error("HTTP error in OpenAI embeddings", status_code=e.response.status_code, error=e)
            raise
        except httpx.RequestError as e:
            logger.error("Request error in OpenAI embeddings", error=str(e))
            raise
        except (KeyError, ValueError) as e:
            logger.error("Response parsing error in OpenAI embeddings", error=str(e))
            raise