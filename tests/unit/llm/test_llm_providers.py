from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bina.application.ports.llm_provider import LLMProvider
from src.bina.infrastructure.llm.providers.qwen_provider import QwenProvider


@pytest.fixture
def qwen_provider() -> QwenProvider:
    """Фикстура для Qwen провайдера."""
    return QwenProvider(api_key="test-key")


def test_qwen_provider_implements_interface(qwen_provider: QwenProvider) -> None:
    """Проверка, что Qwen провайдер реализует интерфейс."""
    assert isinstance(qwen_provider, LLMProvider)


@pytest.mark.asyncio
async def test_qwen_complete_method_signature(qwen_provider: QwenProvider) -> None:
    """Проверка сигнатуры метода complete."""
    # Проверяем только сигнатуру, без реального вызова
    assert hasattr(qwen_provider, "complete")
    assert callable(qwen_provider.complete)


@pytest.mark.asyncio  
async def test_qwen_complete_structured_method_signature(qwen_provider: QwenProvider) -> None:
    """Проверка сигнатуры метода complete_structured."""
    # Проверяем только сигнатуру, без реального вызова
    assert hasattr(qwen_provider, "complete_structured")
    assert callable(qwen_provider.complete_structured)