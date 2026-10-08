# bina.ai — Frontend

Telegram Mini App для аренды недвижимости в Грузии. React 19 + TypeScript + Vite + Tailwind CSS 4.

## Запуск локально

Нужны Node.js 20+ и Python-окружение `_dev/.venv` (mock API).

```powershell
# 1. Mock API (FastAPI, порт 8000)
cd _dev
.\.venv\Scripts\Activate.ps1
uvicorn server:app --reload --port 8000

# 2. Во втором терминале — React dev server (порт 5173, /api проксируется на 8000)
npm install
npm run dev
```

Открыть: http://localhost:5173

| Страница | URL |
|---|---|
| Главная | `/` (пагинация `?page=2`) |
| Квартира (#1 — полная, 4 фото) | `/listing/1` |
| 404 | `/listing/999` |
| Тест карточки | `/test_card` |
| Вход | `/auth` (ошибка Google: `/auth?error=google`) |

Язык: `?lang=ka|ru|en` или переключатель в шапке, выбор сохраняется в `localStorage` (`bina_lang`).

Настройки — в `.env` (пример: `.env.example`): `VITE_BOT_USERNAME` — username бота для кнопки «Открыть в Telegram».
`VITE_ENABLE_WEB_AUTH=true` — показать вход через Google и email в браузере. По умолчанию выключен: бэкенд `/api/auth/*` ещё не сделан (задачи JWT/OAuth).

## Сборка

```powershell
npm run build      # tsc + vite build → dist/
```

`dist/` — статические файлы. Сервер должен отдавать их и на любой неизвестный путь возвращать
`dist/index.html` (SPA fallback), кроме `/api/...`. Пример — `_dev/server.py`: после `npm run build`
всё приложение доступно на http://127.0.0.1:8000.

## API, которое ждёт фронтенд

Эталонная mock-реализация — `_dev/mock_api.py`. Все ответы — JSON.

| Метод | Путь | Ответ |
|---|---|---|
| GET | `/api/listings?page=&per_page=&q=&district=&min_price=&max_price=&rooms=&min_area=&max_area=&floor_min=&floor_max=&not_first_floor=&not_last_floor=&bedrooms=&bathrooms=&features=&condition=&owner_only=&city=&rent_period=` | `{items, total, page, pages}` |
| GET | `/api/listings/{id}` | объект квартиры (без телефона и Telegram владельца), 404 если нет |
| GET | `/api/listings/{id}/similar` | `{items}` — до 3 похожих |
| GET | `/api/listings/{id}/phone` | `{phone}`, 404 если номера нет |
| POST | `/api/listings/{id}/contact` | `{url}` — куда вести пользователя («Написать»): `https://t.me/...`, внешняя или внутренняя ссылка |
| GET | `/api/districts` | `{items: [{id, name: {ka, ru, en}}]}` |

### Авторизация

**В Telegram** отдельного логина нет: каждый запрос несёт заголовок `X-Telegram-Init-Data`, бэкенд проверяет
подпись и сам регистрирует пользователя при первом обращении. JWT не используется. После «Выйти» фронтенд
перестаёт отправлять заголовок, пока пользователь снова не нажмёт «Войти через Telegram».

**В браузере** (UI готов, mock — `_dev/mock_api.py`): сессия — HttpOnly cookie, которую ставит бэкенд
(`SameSite=Lax`); фронтенд токены не хранит и не отправляет.

| Метод | Путь | Тело | Ответ |
|---|---|---|---|
| POST | `/api/auth/register` | `{first_name, email, password}` (пароль ≥ 8) | 201 `{user}` + cookie; 409 — email занят; 422 — валидация |
| POST | `/api/auth/login` | `{email, password}` | 200 `{user}` + cookie; 401 — неверные данные |
| GET | `/api/auth/me` | — | 200 `{user}`; 401 — нет сессии |
| POST | `/api/auth/logout` | — | 204, cookie удалена |
| GET | `/api/auth/google/login?return_to=/auth` | — | 302 на Google → callback бэкенда → cookie → 302 на `return_to`; при ошибке 302 на `return_to?error=google`. `return_to` — только путь этого сайта (защита от open redirect) |

`user`: `{id, first_name, last_name?, username?, photo_url?, email?}`.

### Сохранённые поиски (бэкенд — TASK-028)

Нужен `X-Telegram-Init-Data`, без него — 401 (фронтенд показывает «Откройте в Telegram»). Пока эндпоинта нет
(404) или нет сети, фронтенд работает с mock в `localStorage` (`bina:saved_searches`).

| Метод | Путь | Тело | Ответ |
|---|---|---|---|
| GET | `/api/searches` | — | `{items: SavedSearch[]}` |
| POST | `/api/searches` | `{name?, filters, notify}` | 201 `SavedSearch`; без `name` сервер собирает его из фильтров |
| PATCH | `/api/searches/{id}` | `{name?, notify?}` | `SavedSearch`; 404 — нет такого |
| DELETE | `/api/searches/{id}` | — | 204; 404 — нет такого |

`SavedSearch`: `{id, name, filters, notify, new_count, created_at}`. `filters` — все фильтры поиска (FRONTEND-017): `district` / `districts[]`, `min_price`, `max_price`, `rooms`, `min_area`, `max_area`, `q`, `floor_min`, `floor_max`, `not_first_floor`, `not_last_floor`, `bedrooms`, `bathrooms`, `features[]`, `condition[]`, `owner_only`, `city`, `rent_period`. В ответе незаданные поля — `null` / `[]` / `false`, `rent_period` — `monthly`; фронт их отбрасывает. `features` и `condition` в адресе и в `/api/listings` — через запятую.
`rooms=4` — «4 и больше» (и в `/api/listings`). Фильтры главной хранятся в адресе: `/?district=..&min_price=..&max_price=..&rooms=..&page=..`.

Тексты с бэкенда (`title`, `description`, `address`, `owner.name`, `district.name`) — объект `{ka, ru, en}` или строка.
Типы — `src/api/types.ts`.

## Структура

См. раздел «Структура папки frontend» в `CLAUDE.md`. `legacy/` — старая версия на Jinja2/Alpine.js,
только для справки, будет удалена.
