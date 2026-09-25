from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from bina.application.ports.llm_provider import LLMProvider

logger = structlog.get_logger(__name__)


class AnthropicProvider(LLMProvider):
    """Заглушка для Anthropic провайдера."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        model: str = "claude-3-opus-20240229",
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Ленивый инициализатор HTTP клиента."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
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
    async def complete(self, prompt: str) -> str:
        """Генерирует текстовый ответ на промпт."""
        logger.debug("Completing prompt with Anthropic", prompt=prompt[:100] + "...")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/messages",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                },
            )
            response.raise_for_status()
            
            data = response.json()
            result: str = data["content"][0]["text"]
            logger.debug("Completed prompt successfully", result_length=len(result))
            return result
            
        except (httpx.HTTPStatusError, httpx.RequestError, KeyError, ValueError) as e:
            logger.error("Error in Anthropic completion", error=str(e))
            raise NotImplementedError("Anthropic provider is a stub")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def complete_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Генерирует структурированный ответ в соответствии со схемой."""
        logger.debug("Completing structured prompt with Anthropic", prompt=prompt[:100] + "...")
        
        # Заглушка - всегда вызываем NotImplementedError
        logger.warning("Anthropic structured completion is not implemented")
        raise NotImplementedError("Anthropic provider is a stub")