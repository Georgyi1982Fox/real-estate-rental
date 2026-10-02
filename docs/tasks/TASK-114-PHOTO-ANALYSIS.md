# TASK-114: AI-анализ фото квартиры (ремонт, плесень, дефекты)

## Решения владельца
- Уровень ремонта по фото видят **все** (значок «🛠»), подробный разбор — **Premium**.

## Что видно
- **Все:** «🛠 отличный ремонт» / «🛠 хороший ремонт» / «🛠 нужен ремонт» — в карточках бота
  и `repair_level` в API (`excellent` / `good` / `needs_repair`, `null` — фото ещё не
  разобраны).
- **Premium:** `GET /api/listings/{id}/photo-report` — видимые проблемы (плесень, сырость,
  трещины, отслоившаяся краска, старая техника, старая сантехника, изношенная мебель,
  изношенный пол) и 2-3 предложения: общее состояние, что хорошо, что проверить на просмотре.
  Без Premium тот же адрес отдаёт только уровень и `premium_required: true`.

## Как работает
- Раз в час (шаг «photos» в расписании парсера, после перевода и антифрода) AI смотрит до
  4 первых фото новых объявлений без разбора — до `PHOTO_ANALYSIS_LIMIT` объявлений за
  запуск (по умолчанию 50; `0` — выключено). Вручную:
  `docker compose exec scraper bina-scrape photos --limit 50`.
- Для Premium разбор делается сразу при открытии, если его ещё нет или фото поменялись
  (лимит 30 AI-запросов в день на человека).
- Модель — `gpt-4o-mini` через тот же AITUNNEL и ключ `LLM_API_KEY` (фото в низком
  разрешении — дёшево). Свои: `PHOTO_MODEL`, `PHOTO_API_KEY`, `PHOTO_BASE_URL`.
- Фото с сайтов AI получает ссылкой, фото собственников (лежат у нас) — содержимым.
- Таблица `bina_photo_reports` и колонка `repair_level` у объявлений (миграция
  `photo_reports`, применяется сама).

## Код
`application/photo_analysis.py`, `application/ports/photo_analyzer.py`,
`application/use_cases/analyze_photos.py`, `llm/photo_analyzer.py`,
`db/models/photo_reports.py`, `db/repositories/photo_reports.py`,
`api/routes/photo_report.py`, значок — `bot/formatters.py`, шаг — `scrapers/cli.py`.

## Тесты
`tests/unit/llm/test_photo_analyzer.py`, `tests/integration/api/test_photo_report_postgres.py`.

Фронтенд — FRONTEND-037.
