# Bina.ai — правила работы для Claude

Этот файл Claude читает при старте каждой сессии. Здесь — что за проект и как
работать с владельцем, чтобы новая сессия продолжала без потерь.

## Проект
Bina.ai — Telegram-бот и Telegram Mini App для аренды жилья в Грузии (Тбилиси, Батуми).
- Бэкенд: `src/bina/` — Python 3.12, FastAPI (API для Mini App), aiogram (бот),
  SQLAlchemy async + Alembic, PostgreSQL + pgvector, парсеры сайтов (`infrastructure/scrapers/`).
- Фронтенд (Mini App): `frontend/` — React + Vite + TypeScript; публикуется на GitHub Pages
  автоматически после мержа в `develop` (`.github/workflows/deploy.yml`).
- Docker Compose у владельца: db, migrate, api, web (собранный сайт Mini App + nginx на 5173,
  туда смотрит туннель; TASK-123), bot, scraper (расписание раз в час), backup.
- План и статус всех задач: `docs/tasks/ROADMAP.md`; задания: `docs/tasks/TASK-*.md`,
  `docs/tasks/FRONTEND-*.md`. Следующая задача — первая невыполненная в «Очереди» ROADMAP.
  После каждой задачи обновляй ROADMAP.

## Владелец
- Не программист, пишет по-русски. Отвечай по-русски, просто и коротко, без жаргона.
  Кнопки в интерфейсе описывай по шагам: где находится и как называется.
- Команды для его компьютера (Windows, PowerShell) — по одной, каждая отдельным блоком;
  первая всегда `cd C:\Users\Gtorg\Desktop\Claude\real-estate-rental`.
  Обновить всё после мержа: `.\update-bina.bat` (или `git pull` + `docker compose up -d --build`).
- Никогда не проси и не повторяй секреты: BOT_TOKEN, LLM_API_KEY, POSTGRES_PASSWORD и т. п.
  («сюда его не присылайте»). Telegram ID — не секрет.
- Сначала делай, потом кратко отчитывайся: что сделано, как проверить, что дальше.

## Обязательные правила продукта
- Языки: всё в боте и Mini App — полностью на выбранном языке (ka / ru / en), без
  смешения. Есть тесты на это (`test_texts_are_in_their_language` и др.) — не ослабляй их.
- У каждой команды бота есть кнопка в главном меню (тест `test_every_command_has_a_menu_button`).
  Под ответами бота — кнопка «🏠 Главное меню».
- Режим тестирования: `PREMIUM_FOR_ALL=1` (всё бесплатно, пока владелец тестирует);
  перед запуском — `0` (пункт в ROADMAP).

## Git и проверки
- Работай в ветке `feature/backend-telegram-bot` (если её нет — создай от `origin/develop`).
  PR в `develop`; когда CI зелёный — мерджи сам. GitHub удаляет ветку после мержа —
  создай её заново от `develop`. Без force-push, без переписывания чужой истории.
- Перед пушем: `ruff check src tests`, `ruff format --check src tests`, `mypy src tests`,
  полный `pytest`; для фронтенда — `npx tsc --noEmit` и `npm run build` в `frontend/`.
- Интеграционные тесты идут на PostgreSQL с pgvector (`BINA_TEST_DATABASE_URL`).
  Новая миграция Alembic → добавь её в кортеж `MIGRATIONS` в `tests/integration/conftest.py`;
  у каждой таблицы должны быть `created_at` и `updated_at`.
- Нашёл в CI падение — ищи причину, не отключай и не пропускай тесты.

## Сеть облачной среды
Облачная среда «Default» настроена с доступом к сети **Full** (нужно для парсеров сайтов
недвижимости и проверки сайтов). Если сайт отвечает 403 через прокси — значит, сессия
запущена до смены настройки или в другой среде: скажи владельцу открыть новую сессию
в среде «Default».
