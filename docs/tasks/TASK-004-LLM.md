# TASK-004: LLM Gateway (AI-ядро)

## Цель
Создать архитектуру для работы с AI моделями.

## Требования

### 1. Порт
Создать src/bina/application/ports/llm_provider.py:
- Класс LLMProvider (ABC)
- Метод complete(prompt: str) -> str
- Метод complete_structured(prompt: str, schema: dict) -> dict

### 2. Адаптеры
Создать src/bina/infrastructure/llm/providers/:
- qwen_provider.py (через AITUNNEL)
- anthropic_provider.py (заглушка)
- openai_provider.py (заглушка)

Каждый:
- async через httpx
- retry 3 попытки
- timeout 30 сек
- логирование structlog

### 3. Factory
Создать src/bina/infrastructure/llm/llm_factory.py:
- Возвращает провайдер из конфига
- Fallback цепочка

### 4. Structured Output
Создать src/bina/infrastructure/llm/structured_output.py:
- Валидация через Pydantic
- Автоповтор (макс 2 раза)

### 5. Промпты
Создать src/bina/infrastructure/llm/prompts/:
- translate_listing.py
- detect_fraud.py

### 6. Семантический кэш
Создать src/bina/infrastructure/llm/semantic_cache.py:
- Redis кэш
- TTL 24 часа

### 7. Конфиг
Добавить в settings:
- LLM_PROVIDER, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

## Definition of Done
1. Все адаптеры с тестами
2. Factory работает
3. Structured output валидирует
4. ruff и mypy проходят
5. Показать список файлов