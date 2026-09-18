import asyncio
from typing import TypeVar

import structlog
from pydantic import BaseModel, ValidationError

from src.bina.application.ports.llm_provider import LLMProvider

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


async def complete_structured_with_validation(
    provider: LLMProvider,
    prompt: str,
    response_model: type[T],
    max_retries: int = 2,
) -> T:
    """Выполняет структурированный запрос с валидацией через Pydantic."""
    schema = response_model.model_json_schema()
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Attempt {attempt + 1} for structured completion")
            
            # Получаем сырые данные от LLM провайдера
            raw_data = await provider.complete_structured(prompt, schema)
            
            # Валидируем через Pydantic
            validated_result = response_model.model_validate(raw_data)
            logger.debug("Structured completion validated successfully")
            return validated_result
            
        except (ValidationError, ValueError, KeyError) as e:
            last_error = e
            logger.warning(
                f"Validation failed on attempt {attempt + 1}", 
                error=str(e), 
                raw_data=str(raw_data) if 'raw_data' in locals() else "not available"
            )
            
            if attempt < max_retries:
                # Добавим уточнение к промпту для следующей попытки
                prompt += "\n\nPlease ensure your response strictly follows the required JSON schema."
                await asyncio.sleep(1)  # Небольшая пауза между попытками
            else:
                logger.error("All validation attempts failed", error=str(e))
                raise last_error
    
    # Это никогда не должно произойти, но для статического анализа
    raise last_error or RuntimeError("Structured completion failed")