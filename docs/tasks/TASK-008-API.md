# TASK-008: REST API для Telegram Mini App

## Контекст
Проект Bina.ai. Фронтенд (React, Telegram Mini App) задеплоен на GitHub Pages
(`https://georgyi1982fox.github.io`), но не получает данные: нет REST API.
Стек: Python 3.12, FastAPI, uvicorn, SQLAlchemy 2.0 (async), PostgreSQL + pgvector.

## Цель
FastAPI-сервер, который отдаёт фронтенду объявления, районы и избранное пользователя
поверх существующих репозиториев и use cases.

## Требования

### 1. Сервер
`src/bina/infrastructure/api/`:
```
api/
├── server.py        # create_app(), app, CLI `bina-api`
├── settings.py      # ApiSettings.from_env()
├── auth.py          # проверка подписи X-Telegram-Init-Data
├── dependencies.py  # сессия БД, настройки, текущий пользователь
├── schemas.py       # схемы ответов (контракт frontend/src/api/types.ts)
└── routes/
    ├── listings.py  # /api/listings, /api/listings/{id}, /api/listings/{id}/similar
    ├── districts.py # /api/districts
    ├── favorites.py # /api/favorites
    └── common.py    # 404/422, разбор параметров
```
- Используются `ListingsRepository`, `FavoritesRepository`, `DistrictsRepository`, `UsersRepository`
  и use cases `SearchListingsUseCase`, `GetFavoritesUseCase`, `AddFavoriteUseCase`,
  `RemoveFavoriteUseCase`, `RegisterUserUseCase`.
- Новые use cases `AddFavoriteUseCase` и `RemoveFavoriteUseCase` (`application/use_cases/favorites.py`):
  идемпотентные добавление и удаление (в отличие от `ToggleFavoriteUseCase` бота).
- Сессия БД на запрос; изменения фиксирует эндпоинт, остальное откатывается.

### 2. Эндпоинты

| Метод | Путь | Ответ |
|---|---|---|
| GET | `/api/health` | `{"status": "ok"}` |
| GET | `/api/listings?page=&per_page=&district=&min_price=&max_price=&rooms=` | `{items, total, page, pages}` |
| GET | `/api/listings/{id}` | объявление; 404, если нет, удалено или ID не UUID |
| GET | `/api/listings/{id}/similar` | `{items}`: до 3 объявлений того же района с ценой ±30% |
| GET | `/api/districts` | `{items: [{id, name: {ka, ru, en}}]}` |
| GET | `/api/favorites?user_id=&page=&per_page=` | `{items, total, page, pages}` |
| POST | `/api/favorites` (тело `{"listing_id": "<uuid>"}`) | 201 `{listing_id, is_favorite: true}`; 404, если объявления нет |
| DELETE | `/api/favorites/{listing_id}?user_id=` | 204 (и если записи не было) |

- `page` нумеруется с 1, `per_page` от 1 до 50 (по умолчанию 20). Объявления: только активные и не удалённые, новые сверху.
- `rooms=4` означает «4 и больше» (как в `FilterPanel` фронтенда). Пустые параметры (`district=`) игнорируются.
- Формат объявления:
  ```json
  {
    "id": "0b6d…-uuid", "title": {"ka": "…", "ru": "…"}, "description": {"ka": "…", "ru": "…"},
    "price": 1200.0, "currency": "GEL", "rooms": 2, "area": 55.0,
    "district": "<uuid района>", "is_verified": false, "images": []
  }
  ```
- Документация OpenAPI: `/docs` (Swagger UI).

### 3. Авторизация избранного
Mini App передаёт `Telegram.WebApp.initData` в заголовке `X-Telegram-Init-Data`
(так уже делает `frontend/src/api/client.ts`). Сервер проверяет подпись токеном бота
(`BOT_TOKEN`) и срок жизни (`API_INIT_DATA_MAX_AGE`) и по ним определяет пользователя.
При первом обращении пользователь регистрируется (язык берётся из Telegram).

- `?user_id=` необязателен. Если передан, он должен совпадать с пользователем из подписи, иначе 403.
- Без заголовка ответ 401. `BOT_TOKEN` не задан: 503.
- **Почему не только `user_id`:** его может подставить кто угодно и читать или менять чужое избранное.
- Для локальной отладки из браузера или curl без Telegram есть `API_ALLOW_INSECURE_USER_ID=true`:
  тогда `?user_id=<telegram id>` принимается без подписи. **Никогда не включать в проде.**

### 4. CORS
`CORSMiddleware`: origin из `API_CORS_ORIGINS` (по умолчанию `https://georgyi1982fox.github.io`),
`allow_credentials=True`, методы `GET, POST, DELETE, OPTIONS`,
заголовки `Accept, Content-Type, X-Telegram-Init-Data`.

### 5. Запуск
Точка входа `bina-api = "bina.infrastructure.api.server:cli"`:
```bash
bina-api                         # 0.0.0.0:8000
bina-api --host 127.0.0.1 --port 8000 --reload
uvicorn bina.infrastructure.api.server:app   # альтернатива
```
PowerShell:
```powershell
$env:DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/bina"
$env:BOT_TOKEN="<токен от @BotFather>"
bina-api
```
В dev-режиме Vite (`npm run dev`) проксирует `/api` на `127.0.0.1:8000`, CORS там не нужен.

### 5a. Демо-данные для локальной проверки
Пока парсер не сохраняет объявления (отдельная задача), базу можно наполнить демо-данными
фронтенда (`frontend/mock_data.json`: 6 районов, 12 квартир):
```bash
bina-seed            # из корня репозитория; нужен DATABASE_URL
bina-seed --reset    # удалить демо-квартиры (районы остаются)
```
Квартиры помечаются `source_name = "demo"`, повторный запуск обновляет их, а не дублирует
(`src/bina/infrastructure/db/seed.py`).

### 6. Конфигурация
| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/bina` | БД |
| `BOT_TOKEN` | — | Проверка подписи initData (без него избранное отвечает 503) |
| `API_CORS_ORIGINS` | `https://georgyi1982fox.github.io` | Разрешённые origin через запятую |
| `API_INIT_DATA_MAX_AGE` | `86400` | Срок жизни initData, секунды |
| `API_ALLOW_INSECURE_USER_ID` | `false` | Разрешить `?user_id=` без подписи (только локально) |

### 7. Тесты
- `tests/unit/api/` (44 теста): эндпоинты поверх in-memory репозиториев (`tests/support/fakes.py`),
  фильтры и пагинация, 404/422, подпись initData (подделка, чужой токен, просрочка, несовпадение `user_id`),
  режим `API_ALLOW_INSECURE_USER_ID`, CORS, настройки.
- `tests/integration/api/`: API на PostgreSQL + pgvector (`BINA_TEST_DATABASE_URL`, база очищается).
- Use cases: `tests/unit/application/use_cases/test_favorites.py`.
- Демо-данные: `tests/integration/db/test_seed_postgres.py`, `tests/unit/db/test_seed_cli.py`.

## Что нужно сделать во фронтенде (вне этой задачи)
1. **Базовый URL API.** `client.ts` делает `fetch('/api/...')` относительно страницы. На GitHub Pages
   запросы уйдут на `github.io`, а не на сервер API. Нужна переменная вроде `VITE_API_BASE_URL`
   и `fetch(API_BASE + path)`.
2. **ID объявлений это UUID.** `ListingPage.tsx` проверяет `/^\d+$/` и не открывает объявления
   с UUID; тип `Listing.id` в `types.ts` должен быть `string`.
3. **Избранное.** `useFavorite` пока локальный; нужно подключить GET/POST/DELETE `/api/favorites`,
   а в `client.ts` добавить методы `DELETE` и отправку JSON-тела в `POST`.
4. `/api/listings/{id}/phone` и `/api/listings/{id}/contact` не реализованы: в БД нет телефонов
   и контактов владельцев. `images` пока всегда пустой список (парсер не сохраняет фото).

## Definition of Done
1. ✅ Эндпоинты listings, listings/{id}, favorites (GET/POST/DELETE) + districts, similar, health
2. ✅ Используются существующие репозитории и use cases
3. ✅ CORS для GitHub Pages
4. ✅ CLI `bina-api`
5. ✅ Пользователь избранного определяется по подписи Telegram
6. ✅ Тесты (unit + интеграционные на PostgreSQL), ruff и mypy для нового кода
7. ⏳ Фронтенд переключён на API (см. раздел выше)

## Запреты
- Доверять `user_id` без проверки подписи в проде
- Синхронные запросы к БД
- `allow_origins=["*"]` вместе с `allow_credentials=True`
- Изменения в `frontend/`
