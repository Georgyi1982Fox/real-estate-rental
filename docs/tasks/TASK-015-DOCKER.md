# TASK-015: Docker Compose — весь бэкенд одной командой

> В `BACKEND_ROADMAP.md` это **TASK-039 «Docker Compose»** (и часть TASK-051: образ не от root, кэш зависимостей).

## Цель
Вместо нескольких окон PowerShell (база, API, бот, парсер) — одна команда. Сервисы работают
в фоне, сами перезапускаются после сбоя и после перезагрузки компьютера (если Docker Desktop
запускается вместе с Windows). Эти же файлы понадобятся для переезда на сервер.

## Что сделано
| Файл | Что это |
|---|---|
| `Dockerfile` | Образ бэкенда (Python 3.12 slim): API, бот, парсер, миграции. Зависимости — отдельным слоем (быстрая пересборка), запуск не от root |
| `docker-compose.yml` | Сервисы `db` (PostgreSQL 16 + pgvector), `migrate` (миграции при каждом запуске), `api`, `bot`, `scraper` |
| `.env.example` | Пример настроек; копируется в `.env` (не попадает в Git) |
| `.dockerignore` | В образ не попадают фронтенд, тесты, `.env` |
| CI | Job `Docker (compose config, image build)`: конфиг валиден, образ собирается |

- `api` слушает `127.0.0.1:8000` — как раньше, поэтому туннель Cloudflare и `npm run dev` работают без изменений.
- `db` доступна с компьютера на `127.0.0.1:5434` (старая `bina-db` занимает 5433).
- Данные базы — в томе `db-data`: сохраняются при `docker compose down` и пересборке.
- **Исправлено попутно:** первая миграция не включала расширение `vector` — на новой пустой базе
  `alembic upgrade head` падал (старая база создавалась вручную, тесты включали расширение сами).

Фронтенд (`npm run dev`) и туннель (`cloudflared`) пока запускаются как раньше — их перенесём
при переезде на сервер.

---

## Запуск на Windows (первый раз)

Нужен **Docker Desktop** (он уже стоит — в нём работает `bina-db`). В PowerShell, в папке проекта:

**1. Обновить код**
```powershell
git pull
```

**2. Настройки**
```powershell
copy .env.example .env
notepad .env
```
Заполнить и сохранить:
- `POSTGRES_PASSWORD` — придумать пароль (латиница и цифры);
- `BOT_TOKEN` — токен бота;
- `LLM_API_KEY`, `LLM_MODEL` — когда будет ключ AITUNNEL (можно пусто).

**3. Остановить старые окна.** В окнах API, бота и автозапуска парсера — `Ctrl+C`, окна закрыть.
Окна **туннеля** (`cloudflared`) и **сайта** (`npm run dev`) — не трогать.

**4. Перенести данные из старой базы** (квартиры, избранное, поиски). Иначе новая база будет
пустой и парсер заполнит квартиры заново, но избранное и сохранённые поиски пропадут.
```powershell
docker start bina-db
```
```powershell
docker exec bina-db pg_dump -U postgres -d bina -Fc -f /tmp/bina.dump
```
```powershell
docker cp bina-db:/tmp/bina.dump bina.dump
```
```powershell
docker compose up -d db
```
Подождать 10 секунд, затем:
```powershell
docker compose cp bina.dump db:/tmp/bina.dump
```
```powershell
docker compose exec db pg_restore -U postgres -d bina --clean --if-exists --no-owner /tmp/bina.dump
```
```powershell
docker stop bina-db
```
Старую `bina-db` не удаляем — пусть полежит как резервная копия.

**5. Запустить всё**
```powershell
docker compose up -d --build
```
Первый раз — несколько минут (скачивание и сборка), дальше — секунды.

**6. Проверить**
```powershell
docker compose ps
```
`db`, `api`, `bot`, `scraper` — `Up` (у `api` и `db` — `healthy`), `migrate` — `Exited (0)` (так и должно быть).
В браузере: https://bina.test-realtybot.ru/api/health → `{"status":"ok"}`.

---

## Каждый день

| Что | Команда |
|---|---|
| Обновить после `git pull` | `docker compose up -d --build` |
| Что запущено | `docker compose ps` |
| Логи (выход — `Ctrl+C`) | `docker compose logs -f api` (или `bot`, `scraper`, `db`) |
| Перезапустить один сервис | `docker compose restart bot` |
| Остановить всё (данные сохраняются) | `docker compose down` |
| Разовый парсинг / перевод | `docker compose exec scraper bina-scrape --source all --limit 50` |
| Демо-данные | `docker compose exec api bina-seed` |

**Никогда** не запускайте `docker compose down -v` без нужды: `-v` удаляет базу.

## Проверено
- Сборка образа, `docker compose up`: миграции на пустой базе, API (`/api/health`, `/api/listings`,
  формат ошибок), парсер переживает недоступность сайтов и не падает, запуск не от root.
- Данные сохраняются после `docker compose down` / `up`; повторная миграция — без изменений.
- Перенос данных из отдельного контейнера `bina-db` командами из шага 4.

## Definition of Done
1. ✅ `docker compose up -d --build` поднимает базу, миграции, API, бота, парсер
2. ✅ Healthchecks (`db`, `api`), перезапуск сервисов, данные в томе
3. ✅ Настройки в `.env`, пример — `.env.example`
4. ✅ Сборка образа проверяется в CI
5. ⏳ Фронтенд и туннель в Compose, Nginx и HTTPS — при переезде на сервер (TASK-046/047)
