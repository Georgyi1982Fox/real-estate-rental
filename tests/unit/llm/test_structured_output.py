from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from bina.infrastructure.llm.structured_output import complete_structured_with_validation


class _TestModel(BaseModel):
    """Тестовая модель для валидации."""
    name: str
    age: int


@pytest.mark.asyncio
async def test_structured_output_validation_success() -> None:
    """Тест успешной валидации структурированного вывода."""
    # Создаем мокированного провайдера
    provider = AsyncMock()
    provider.complete_structured.return_value = {"name": "John", "age": 30}

    # Выполняем валидацию
    result = await complete_structured_with_validation(provider, "test prompt", _TestModel)

    assert isinstance(result, _TestModel)
    assert result.name == "John"
    assert result.age == 30