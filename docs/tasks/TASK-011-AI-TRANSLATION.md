# TASK-011: AI-перевод объявлений

> В `BACKEND_ROADMAP.md` это **TASK-010 «AI Перевод описаний»**.

## Цель
Парсеры сохраняют объявления на одном языке (MyHome.ge и SS.ge — русский). Mini App и бот
трёхъязычные (ka, ru, en), поэтому недостающие языки заполняются переводом через LLM.

## Требования

### 1. База
Миграция `listing_translations_en`: `title_en` (String), `description_en` (Text),
`NOT NULL DEFAULT ''`. Пустая строка = перевода ещё нет.

### 2. Слой приложения
- Порт `application/ports/translator.py`: `ITranslator.translate(text, source, targets)`,
  `ListingText(title, description)`, `TranslationError`, `LANGUAGES = ("ru", "ka", "en")`.
- Порт `application/repositories/translations.py`: `list_untranslated(limit)`, `save_texts(id, texts)`.
- Use case `application/use_cases/translate_listings.py` — `TranslateListingsUseCase.execute(limit)`:
  объявления с пустым заголовком хотя бы на одном языке → язык-источник (первый заполненный
  из ru, ka, en) → перевод на все пустые языки одним запросом → сохранение.
  Ошибка на одном объявлении не останавливает остальные. Итог: `TranslationStats(checked, translated, failed)`.

### 3. Инфраструктура
- `infrastructure/llm/translator.py` — `LLMTranslator(provider)`: промпт для объявлений об аренде
  (числа, цены, телефоны и адреса без изменений), ответ JSON `{"ka": {"title", "description"}, ...}`,
  проверка Pydantic, повтор при некорректном ответе, `TranslationError` при сбое сети или ответа.
  Используется обычный `complete` (без tool calling), поэтому подходит любая модель провайдера.
- `ListingsRepository.list_untranslated` / `save_texts`.
- **Сброс устаревшего перевода:** если парсер видит, что текст объявления изменился, поля
  других языков очищаются (`stale_translation_resets`), и перевод делается заново. Если текст
  тот же (например, изменилась только цена), перевод сохраняется.
- API отдаёт `title`/`description` с `ka`, `ru`, `en`; бот показывает заголовок на языке
  пользователя (запасные: ru, ka, en).
- Провайдер по умолчанию: Qwen через AITUNNEL (`https://api.aitunnel.ru/v1`, OpenAI-совместимый API).
  Таймаут запроса `LLM_TIMEOUT` (по умолчанию 120 с).

### 4. Запуск
```bash
bina-scrape translate --limit 50                  # перевести до 50 объявлений
bina-scrape schedule --interval 6 --limit 100     # парсинг, затем перевод новых (--translate-limit 200)
bina-scrape schedule --no-translate               # только парсинг
```
Перевод коммитится пачками по 10: сбой посередине не теряет уже переведённое.
Без `LLM_API_KEY` команда `translate` завершается с подсказкой, а `schedule` только парсит.

### 5. Конфигурация
| Переменная | По умолчанию | Описание |
|---|---|---|
| `LLM_API_KEY` | — | Ключ AITUNNEL (обязательно) |
| `LLM_PROVIDER` | `qwen` | `qwen` (любой OpenAI-совместимый API, в т. ч. AITUNNEL) |
| `LLM_BASE_URL` | `https://api.aitunnel.ru/v1` | Адрес API (сверить в кабинете AITUNNEL) |
| `LLM_MODEL` | `qwen-max` | Модель из каталога AITUNNEL |
| `LLM_TIMEOUT` | `120` | Таймаут запроса, секунды |

### 6. Тесты
- `tests/unit/application/use_cases/test_translate_listings.py`: выбор языков, ошибки.
- `tests/unit/infrastructure/llm/test_translator.py`: промпт, разбор ответа (в т. ч. в markdown), повтор, ошибки сети.
- `tests/unit/infrastructure/scrapers/test_cli.py`: `translate`, пачки с коммитом, перевод в `schedule`.
- `tests/integration/scrapers/test_translations_postgres.py`: миграция, выборка, сохранение,
  сброс при изменении текста, три языка в API.

Попутно: нормализатор цены понимает символы валют `₾`, `$`, `€` (падавший тест исправлен).

## Definition of Done
1. ✅ Перевод на недостающие языки (ru, ka, en), structured output с проверкой
2. ✅ Интеграция с автозапуском парсера
3. ✅ Повторно переводятся только изменившиеся объявления (вместо Redis-кэша)
4. ✅ Тесты (unit + PostgreSQL), ruff и mypy для нового кода
5. ⏳ Проверка на настоящем ключе AITUNNEL
