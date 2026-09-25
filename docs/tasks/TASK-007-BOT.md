# TASK-007: Telegram-бот

> Документ составлен по факту реализации (ветка `feature/backend-telegram-bot`).
> Исходный файл задачи не был запушен, требования восстановлены по описанию.

## Контекст
Проект Bina.ai: Telegram Mini App для аренды жилья в Грузии.
Бот служит входной точкой: регистрирует пользователя, даёт искать объявления
и вести избранное прямо в чате, открывает Mini App.
Стек: Python 3.12, aiogram 3.x, SQLAlchemy 2.0 (async), PostgreSQL + pgvector.

## Цель
Рабочий бот в режимах polling (разработка) и webhook (прод), интегрированный
с существующими моделями и репозиториями.

## Требования

### 1. Репозитории
Порты (`src/bina/application/repositories/`) и реализации (`src/bina/infrastructure/db/repositories/`):
- `IUsersRepository` / `UsersRepository`: `get_by_id`, `get_by_telegram_id`, `create`, `update_language`.
  `create` делает upsert по `telegram_id`: устойчив к гонке двух первых апдейтов и восстанавливает мягко удалённого пользователя.
- `IFavoritesRepository` / `FavoritesRepository`: `add` (идемпотентно), `remove`, `exists`,
  `filter_favorite_ids`, `list_by_user`, `count_by_user` (удалённые объявления не учитываются).
- `IListingsRepository.search(filters, limit, offset)` и `count(filters)`: только активные, не удалённые объявления, новые сверху.
- `IDistrictsRepository.list_all()` и `get_by_id()`.
- DTO `ListingSearchFilters` (`application/dtos/listing_search.py`): район, диапазоны цены и комнат (включительно, `None` = без ограничения).
- DTO `Page[T]` (`application/dtos/pagination.py`).

### 2. Use cases (`src/bina/application/use_cases/`)
- `RegisterUserUseCase` (`register_user.py`): найти или создать пользователя. Язык берётся из `language_code`
  Telegram (`en-US` → `en`, неподдерживаемый → `ru`) только при создании.
- `SearchListingsUseCase` (`search_listings.py`): постраничный поиск.
- `ToggleFavoriteUseCase`, `GetFavoritesUseCase` (`favorites.py`). Добавить удалённое или несуществующее
  объявление нельзя (`ListingNotFoundError` из `application/errors.py`).

Use cases зависят только от портов.

### 3. Бот (`src/bina/infrastructure/bot/`)
```
bot/
├── settings.py        # BotSettings.from_env(), BotMode
├── texts.py           # тексты ru/en, t(), ui_language()
├── formatters.py      # карточки объявлений (HTML), цены, районы
├── factory.py         # create_bot, create_dispatcher, setup_bot_ui
├── runner.py          # run_polling, run_webhook, build_webhook_app
├── cli.py             # bina-bot polling | webhook
├── middlewares/
│   ├── db.py          # DbSessionMiddleware: транзакция на апдейт
│   └── registration.py# RegistrationMiddleware: user, is_new_user, user_language
├── keyboards/
│   ├── callbacks.py   # CallbackData-фабрики
│   ├── filters.py     # пресеты цен и комнат → ListingSearchFilters
│   ├── search.py      # районы, цена, комнаты, результаты
│   ├── listings.py    # кнопки ☆/★, пагинация, flip_favorite_button
│   ├── favorites.py, profile.py, menu.py
└── handlers/          # каждый модуль отдаёт create_router()
    ├── start.py, help.py, search.py, favorites.py, profile.py
    ├── fallback.py    # нераспознанные сообщения
    └── errors.py      # лог + сообщение пользователю
```

**Команды и сценарии:**
- `/start`: регистрация, приветствие (разное для нового и вернувшегося), reply-меню
  «🔍 Поиск / ❤️ Избранное / 👤 Профиль».
- `/search`: мастер район → бюджет → комнаты → результаты по `BOT_PAGE_SIZE` с пагинацией.
  Если районов в БД нет, сразу показываются все объявления.
- `/favorites`: список избранного с пагинацией.
- `/profile`: язык, подписка, баланс, число избранных, дата регистрации; смена языка (ru/en/ka).
- `/help`: справка.
- Кнопки ☆/★ под списками добавляют или убирают объявление из избранного и меняют только звезду на кнопке.

**Ключевые решения:**
- **Поиск без FSM.** Все фильтры и номер страницы кодируются в callback data
  (≤ 64 байт, проверено тестом). Кнопки работают после перезапуска бота, Redis не нужен.
- **Транзакция на апдейт.** `DbSessionMiddleware` делает commit после успешной обработки и rollback при исключении.
  Обработчик ошибок берёт язык из `user_language` (строка), потому что после rollback ORM-объект `user` недоступен.
- **Апдейты без отправителя-человека** (анонимные админы групп, боты) отбрасываются в `RegistrationMiddleware`.
- **Роутеры создаются фабриками** (`create_router()`), поэтому в одном процессе можно собрать несколько Dispatcher (тесты).
- **Язык `ka`**: интерфейс пока английский, заголовки объявлений грузинские.
- Цены в пресетах в GEL (нормализатор парсера приводит цены к лари).

### 4. Запуск (CLI)
Точка входа `bina-bot` (pyproject.toml):
```bash
bina-bot polling [--drop-pending-updates]
bina-bot webhook [--host HOST] [--port PORT] [--drop-pending-updates]
bina-bot --log-level DEBUG polling
```
- `polling` снимает активный вебхук, регистрирует команды и запускает long polling.
- `webhook` поднимает встроенный aiohttp-сервер aiogram: `POST BOT_WEBHOOK_PATH` (проверка секрета,
  401 без него) и `GET /health`. При старте регистрирует вебхук в Telegram.
  TLS терминирует обратный прокси. В TASK-008 вебхук переедет в FastAPI.

### 5. Конфигурация
| Переменная | По умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — | Токен от @BotFather (обязательно) |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/bina` | БД (`DatabaseManager`) |
| `BOT_MODE` | `polling` | Режим по умолчанию; команда CLI имеет приоритет |
| `BOT_WEBHOOK_BASE_URL` | — | Публичный HTTPS-адрес (обязательно для webhook) |
| `BOT_WEBHOOK_PATH` | `/telegram/webhook` | Путь вебхука |
| `BOT_WEBHOOK_SECRET` | — | Секрет заголовка `X-Telegram-Bot-Api-Secret-Token` (в проде обязателен по смыслу) |
| `BOT_WEBAPP_HOST` / `BOT_WEBAPP_PORT` | `0.0.0.0` / `8080` | Адрес aiohttp-сервера |
| `BOT_MINI_APP_URL` | — | URL Mini App: кнопка меню чата и кнопки под списками |
| `BOT_PAGE_SIZE` | `5` | Объявлений на страницу (1–10) |
| `BOT_DROP_PENDING_UPDATES` | `false` | Пропустить накопившиеся апдейты |

### 6. Тесты
- `tests/unit/application/`: use cases, `ListingSearchFilters`.
- `tests/unit/bot/` (148 тестов): сценарии через настоящий Dispatcher с фейковым Telegram
  (`tests/support/telegram.py`) и in-memory репозиториями; клавиатуры, тексты, форматтеры,
  настройки, middleware, CLI, webhook-сервер.
- `tests/integration/bot/`: репозитории и полный сценарий бота на PostgreSQL + pgvector.
  Запуск: `BINA_TEST_DATABASE_URL=postgresql+asyncpg://... pytest tests/integration/bot`
  (**база очищается**; без переменной тесты пропускаются).

## Изменения вне пакета бота
- `db/models`: недостающие `TYPE_CHECKING`-импорты (mypy); `value_enum()` в `base.py`:
  enum `User.role`, `User.subscription_tier`, `Listing.status` хранятся значениями (`user`, `active`),
  как в миграции. Раньше любой INSERT пользователя и фильтр по статусу падали.
- `DatabaseManager`: публичные `session_factory` и `dispose()`.
- `pyproject.toml`: `aiogram`, `click`, `pytest-asyncio`; entry point `bina-bot`;
  pytest `--import-mode=importlib` + `pythonpath=["."]` (весь набор тестов раньше не собирался);
  ruff `allowed-confusables` для кириллицы.
- `.gitignore`; из git удалены закоммиченные `.pyc`.

## Известные проблемы (вне TASK-007)
- Миграция `initial_db_structure` использует `Vector` без импорта: `alembic upgrade head` падает.
- `server_default="gen_random_uuid()"` задан строкой: `Base.metadata.create_all` падает.
- Enum в `Payment` хранятся именами (та же проблема, что была у `User` и `Listing`).
- `ListingsRepository.create_or_update_from_raw` пишет в несуществующие поля `Listing`
  (`title`, `description`, `url`, `photos`): 5 ошибок mypy.
- 9 падающих тестов парсера (`tests/*/infrastructure/scrapers/`), были до TASK-007.

## Definition of Done
1. ✅ Бот отвечает на /start, /search, /favorites, /profile, /help
2. ✅ Клавиатуры фильтров: район, цена, комнаты
3. ✅ Middleware регистрации пользователя и сессии БД
4. ✅ Интеграция с репозиториями Users, Listings, Favorites, Districts
5. ✅ CLI: `bina-bot polling` / `bina-bot webhook`
6. ✅ Тесты в `tests/unit/bot/` (+ интеграционные на PostgreSQL)
7. ✅ ruff и mypy проходят для нового кода
8. ⏳ Проверка polling на реальном токене (нужен тестовый бот от @BotFather)

## Запреты
- Синхронные запросы к БД и Telegram
- Бизнес-логика в хендлерах: регистрация, поиск и избранное идут через use cases
  (смена языка пока вызывает `UsersRepository.update_language` напрямую)
- Хранение состояния поиска на сервере (всё в callback data)
- Изменения в `frontend/`
