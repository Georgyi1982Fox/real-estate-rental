# TASK-005: Use-case перевода объявлений

## Цель
Создать use-case для AI-перевода объявлений с грузинского на русский на английский.

## Требования

### 1. Use-case
Создать src/bina/application/use_cases/translate_listing.py:
- Класс TranslateListingUseCase
- Метод execute(listing_id: UUID) -> TranslatedListingDTO
- Использует LLM Gateway (structured output)
- Сохраняет перевод в БД

### 2. DTO
Создать src/bina/application/dtos/listing_dto.py:
- TranslatedListingDTO (title_ru, description_ru, price, rooms, area)

### 3. Интеграция с LLM
Использовать prompt из translate_listing.py:
- Вход: текст на грузинском
- Выход: JSON с полями title_ru, description_ru
- Валидация через Pydantic

### 4. Кэширование
- Проверять semantic_cache перед вызовом LLM
- Сохранять результат после перевода

### 5. Тесты
- Тест с mock LLM
- Тест с real LLM (через AITUNNEL)

## Definition of Done
1. Use-case работает
2. Перевод сохраняется в БД
3. Кэш работает
4. Тесты проходят
5. Пример использования в ответе