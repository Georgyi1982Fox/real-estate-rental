from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Порт для работы с LLM провайдерами."""

    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Генерирует текстовый ответ на промпт."""
        pass

    @abstractmethod
    async def complete_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Генерирует структурированный ответ в соответствии со схемой."""
        pass