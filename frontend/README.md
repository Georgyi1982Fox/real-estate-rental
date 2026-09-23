# Bina.ai — Frontend

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

Язык: `?lang=ka|ru|en` или переключатель в шапке, выбор сохраняется в `localStorage` (`bina_lang`).

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
| GET | `/api/listings?page=&per_page=&district=&min_price=&max_price=&rooms=` | `{items, total, page, pages}` |
| GET | `/api/listings/{id}` | объект квартиры (без телефона и Telegram владельца), 404 если нет |
| GET | `/api/listings/{id}/similar` | `{items}` — до 3 похожих |
| GET | `/api/listings/{id}/phone` | `{phone}`, 404 если номера нет |
| POST | `/api/listings/{id}/contact` | `{url}` — куда вести пользователя («Написать»): `https://t.me/...`, внешняя или внутренняя ссылка |
| GET | `/api/districts` | `{items: [{id, name: {ka, ru, en}}]}` |

Тексты с бэкенда (`title`, `description`, `address`, `owner.name`, `district.name`) — объект `{ka, ru, en}` или строка.
Типы — `src/api/types.ts`.

## Структура

См. раздел «Структура папки frontend» в `CLAUDE.md`. `legacy/` — старая версия на Jinja2/Alpine.js,
только для справки, будет удалена.
