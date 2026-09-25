    @staticmethod
    def create_embeddings_provider() -> BaseEmbeddingsProvider:
        """Создает провайдера embeddings на основе конфигурации."""
        # Для простоты используем OpenAI embeddings как заглушку
        from bina.infrastructure.llm.providers.openai_embeddings_provider import OpenAIEmbeddingsProvider
        
        api_key = os.getenv("OPENAI_API_KEY", "")
        return OpenAIEmbeddingsProvider(api_key=api_key)