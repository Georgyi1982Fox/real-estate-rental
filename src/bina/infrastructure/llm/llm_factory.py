import os
from typing import TYPE_CHECKING, Any

from bina.application.ports.llm_provider import LLMProvider
from bina.infrastructure.llm.providers.anthropic_provider import AnthropicProvider
from bina.infrastructure.llm.providers.openai_provider import OpenAIProvider
from bina.infrastructure.llm.providers.qwen_provider import AITUNNEL_BASE_URL, QwenProvider

if TYPE_CHECKING:
    from bina.infrastructure.llm.providers.openai_embeddings_provider import (
        OpenAIEmbeddingsProvider,
    )
    from bina.infrastructure.llm.providers.openai_transcription_provider import (
        OpenAITranscriptionProvider,
    )


class LLMFactory:
    """Фабрика для создания LLM провайдеров."""

    @staticmethod
    def create_provider() -> LLMProvider:
        """Создает провайдер на основе конфигурации с fallback цепочкой."""
        # Получаем конфигурацию из переменных окружения
        provider_name = os.getenv("LLM_PROVIDER", "qwen").lower()
        api_key = os.getenv("LLM_API_KEY", "")
        base_url = os.getenv("LLM_BASE_URL", "")
        model = os.getenv("LLM_MODEL", "")

        providers_config: dict[str, tuple[type[LLMProvider], dict[str, Any]]] = {
            # Перевод длинного объявления на два языка идёт дольше 30 с (TASK-010)
            "qwen": (
                QwenProvider,
                {"api_key": api_key, "timeout": int(os.getenv("LLM_TIMEOUT", "120"))},
            ),
            "anthropic": (AnthropicProvider, {"api_key": api_key}),
            "openai": (OpenAIProvider, {"api_key": api_key}),
        }

        # Попробуем основного провайдера
        if provider_name in providers_config:
            provider_class, kwargs = providers_config[provider_name]
            if base_url:
                kwargs["base_url"] = base_url
            if model:
                kwargs["model"] = model

            try:
                return provider_class(**kwargs)
            except (TypeError, ValueError, KeyError) as e:
                print(f"Failed to create {provider_name} provider: {e}")

        # Fallback цепочка: qwen -> openai -> anthropic
        fallback_chain = ["qwen", "openai", "anthropic"]

        for fallback_provider in fallback_chain:
            if fallback_provider == provider_name:
                continue

            provider_class, kwargs = providers_config[fallback_provider]
            if base_url and fallback_provider != provider_name:
                kwargs["base_url"] = base_url
            if model and fallback_provider != provider_name:
                kwargs["model"] = model

            try:
                print(f"Falling back to {fallback_provider} provider")
                return provider_class(**kwargs)
            except (TypeError, ValueError, KeyError) as e:
                print(f"Failed to create fallback {fallback_provider} provider: {e}")
                continue

        raise RuntimeError("Failed to create any LLM provider")

    @staticmethod
    def create_embeddings_provider() -> "OpenAIEmbeddingsProvider":
        """Провайдер embeddings (TASK-012): OpenAI-совместимый API.

        Ключ и адрес — ``EMBEDDINGS_API_KEY`` / ``EMBEDDINGS_BASE_URL``, по умолчанию те же,
        что для перевода: ``LLM_API_KEY`` и ``LLM_BASE_URL``, а без него — адрес провайдера
        по умолчанию (qwen → AITUNNEL, openai → OpenAI).
        Модель — ``EMBEDDINGS_MODEL`` (по умолчанию text-embedding-3-small).
        """
        from bina.infrastructure.llm.providers.openai_embeddings_provider import (
            DEFAULT_MODEL,
            OpenAIEmbeddingsProvider,
        )

        base_url = (
            os.getenv("EMBEDDINGS_BASE_URL")
            or os.getenv("LLM_BASE_URL")
            or _DEFAULT_EMBEDDINGS_URLS.get(os.getenv("LLM_PROVIDER", "qwen").lower())
            or AITUNNEL_BASE_URL
        )
        return OpenAIEmbeddingsProvider(
            api_key=embeddings_api_key(),
            model=os.getenv("EMBEDDINGS_MODEL") or DEFAULT_MODEL,
            base_url=base_url,
        )


def create_speech_provider() -> "OpenAITranscriptionProvider":
    """Распознавание голосовых (умный поиск голосом) — тот же ключ и адрес, что у embeddings.

    Свои можно задать ``STT_API_KEY`` / ``STT_BASE_URL``; модель — ``STT_MODEL``
    (по умолчанию whisper-1).
    """
    from bina.infrastructure.llm.providers.openai_transcription_provider import (
        DEFAULT_MODEL,
        OpenAITranscriptionProvider,
    )

    base_url = (
        os.getenv("STT_BASE_URL")
        or os.getenv("EMBEDDINGS_BASE_URL")
        or os.getenv("LLM_BASE_URL")
        or _DEFAULT_EMBEDDINGS_URLS.get(os.getenv("LLM_PROVIDER", "qwen").lower())
        or AITUNNEL_BASE_URL
    )
    return OpenAITranscriptionProvider(
        api_key=os.getenv("STT_API_KEY") or embeddings_api_key(),
        model=os.getenv("STT_MODEL") or DEFAULT_MODEL,
        base_url=base_url,
    )


# Куда идут embeddings, если адрес не задан: туда же, куда перевод этого провайдера
_DEFAULT_EMBEDDINGS_URLS = {"qwen": AITUNNEL_BASE_URL, "openai": "https://api.openai.com/v1"}


def embeddings_api_key() -> str:
    return os.getenv("EMBEDDINGS_API_KEY") or os.getenv("LLM_API_KEY") or ""


def embeddings_configured() -> bool:
    """Можно ли считать embeddings (есть ключ)."""
    return bool(embeddings_api_key())
