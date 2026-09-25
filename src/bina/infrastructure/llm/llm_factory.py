import os

from bina.application.ports.llm_provider import LLMProvider
from bina.infrastructure.llm.providers.anthropic_provider import AnthropicProvider
from bina.infrastructure.llm.providers.base_embeddings_provider import BaseEmbeddingsProvider
from bina.infrastructure.llm.providers.openai_provider import OpenAIProvider
from bina.infrastructure.llm.providers.qwen_provider import QwenProvider


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
        
        providers_config = {
            "qwen": (QwenProvider, {"api_key": api_key}),
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
                return provider_class(**kwargs)  # type: ignore
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
                return provider_class(**kwargs)  # type: ignore
            except (TypeError, ValueError, KeyError) as e:
                print(f"Failed to create fallback {fallback_provider} provider: {e}")
                continue
        
        raise RuntimeError("Failed to create any LLM provider")

    @staticmethod
    def create_embeddings_provider() -> BaseEmbeddingsProvider:
        """Создает провайдера embeddings на основе конфигурации."""
        # Для простоты используем OpenAI embeddings как заглушку
        from bina.infrastructure.llm.providers.openai_embeddings_provider import OpenAIEmbeddingsProvider
        
        api_key = os.getenv("OPENAI_API_KEY", "")
        return OpenAIEmbeddingsProvider(api_key=api_key)