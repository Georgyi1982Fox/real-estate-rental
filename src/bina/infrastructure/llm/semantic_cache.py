import asyncio
import hashlib
import json
from typing import Any, Optional

import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)


class SemanticCache:
    """Семантический кэш на основе Redis."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_hours: int = 24) -> None:
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.ttl_seconds = ttl_hours * 3600
    
    async def get(self, prompt: str) -> Optional[Any]:
        """Получает результат из кэша по промпту."""
        key = self._generate_key(prompt)
        try:
            cached_result = await self.redis_client.get(key)
            if cached_result:
                result = json.loads(cached_result)
                logger.debug("Cache hit", key=key[:20] + "...")
                return result
        except Exception as e:
            logger.warning("Cache get error", error=str(e))
        return None
    
    async def set(self, prompt: str, result: Any) -> None:
        """Сохраняет результат в кэш."""
        key = self._generate_key(prompt)
        try:
            serialized_result = json.dumps(result, ensure_ascii=False)
            await self.redis_client.setex(key, self.ttl_seconds, serialized_result)
            logger.debug("Cache set", key=key[:20] + "...", ttl_hours=self.ttl_seconds // 3600)
        except Exception as e:
            logger.warning("Cache set error", error=str(e))
    
    def _generate_key(self, prompt: str) -> str:
        """Генерирует ключ для кэша на основе промпта."""
        # Используем SHA-256 хэш для создания уникального ключа
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return f"llm_cache:{prompt_hash}"
    
    async def close(self) -> None:
        """Закрывает соединение с Redis."""
        await self.redis_client.close()