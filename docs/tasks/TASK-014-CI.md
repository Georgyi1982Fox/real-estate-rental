# TASK-014: CI на GitHub Actions

> В `BACKEND_ROADMAP.md` это **TASK-040 «CI/CD»** (часть CI; автодеплой API — вместе с сервером).

## Цель
Каждый PR (и бэкенд, и фронтенд) автоматически проверяется до мержа.

## Что сделано
- `.github/workflows/ci.yml`: на каждый PR в `develop`/`main` и пуш в `develop`.
  - **Backend:** `ruff check`, `ruff format --check`, `mypy src tests`, `pytest` (unit + интеграционные
    на `pgvector/pgvector:pg16`, база `bina_test` в сервисе GitHub Actions).
  - **Frontend:** `npm ci`, `npx tsc --noEmit`, `npm run build`.
- Старый код приведён к правилам, чтобы CI был зелёным с первого запуска: форматирование
  (`ruff format`), 267 замечаний ruff, синтаксическая ошибка в неиспользуемом
  `llm/llm_factory_embeddings.py` (файл удалён), типы в `alembic/env.py` и старых тестах.
- Версии `ruff` и `mypy` закреплены в `pyproject.toml` (`[dev]`).
- Деплой фронтенда на GitHub Pages — прежний `deploy.yml`.

## Проверить у себя перед PR
```bash
pip install -e ".[dev]"
ruff check src tests && ruff format --check src tests && mypy src tests && pytest -q
cd frontend && npx tsc --noEmit && npm run build
```
Автоисправление стиля: `ruff check --fix src tests && ruff format src tests`.

## Рекомендуется включить (настройки GitHub, делает владелец репозитория)
Settings → Branches → правило для `develop` → **Require status checks to pass before merging**,
отметить `Backend (ruff, mypy, pytest)` и `Frontend (tsc, build)`. Тогда красный PR нельзя смержить.

## Definition of Done
1. ✅ Линтер, типы, тесты бэкенда и сборка фронтенда на каждый PR
2. ✅ Интеграционные тесты на PostgreSQL + pgvector в CI
3. ✅ Весь код проходит проверки
4. ⏳ Автодеплой API — после переезда на сервер (TASK-039 и далее)
