import json
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.bina.application.ports.llm_provider import LLMProvider

logger = structlog.get_logger(__name__)


class QwenProvider(LLMProvider):
    """Провайдер для Qwen модели через AITUNNEL."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.aitunnel.com/v1",
        model: str = "qwen-max",
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
                timeout=httpx.Timeout(self.timeout),
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
    async def complete(self, prompt: str) -> str:
        """Генерирует текстовый ответ на промпт."""
        logger.debug("Completing prompt with Qwen", prompt=prompt[:100] + "...")

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()

            data = response.json()
            result: str = data["choices"][0]["message"]["content"]
            logger.debug("Completed prompt successfully", result_length=len(result))
            return result

        except httpx.HTTPStatusError as e:
            logger.error("HTTP error in Qwen completion", status_code=e.response.status_code, error=e)
            raise
        except httpx.RequestError as e:
            logger.error("Request error in Qwen completion", error=str(e))
            raise
        except (KeyError, json.JSONDecodeError) as e:
            logger.error("Response parsing error in Qwen completion", error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def complete_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Генерирует структурированный ответ в соответствии со схемой."""
        logger.debug("Completing structured prompt with Qwen", prompt=prompt[:100] + "...")

        try:
            # Используем инструменты (tools) для структурированного вывода
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "structured_output",
                                "description": "Structured output according to schema",
                                "parameters": schema,
                            },
                        }
                    ],
                    "tool_choice": {"type": "function", "function": {"name": "structured_output"}},
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()

            data = response.json()

            # Извлекаем результат из вызова функции
            tool_calls = data["choices"][0]["message"].get("tool_calls", [])
            if not tool_calls:
                raise ValueError("No tool calls in response")

            result: dict[str, Any] = json.loads(tool_calls[0]["function"]["arguments"])
            logger.debug("Completed structured prompt successfully", result_keys=list(result.keys()))
            return result

        except httpx.HTTPStatusError as e:
            logger.error("HTTP error in Qwen structured completion", status_code=e.response.status_code, error=e)
            raise
        except httpx.RequestError as e:
            logger.error("Request error in Qwen structured completion", error=str(e))
            raise
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            logger.error("Response parsing error in Qwen structured completion", error=str(e))
            raise