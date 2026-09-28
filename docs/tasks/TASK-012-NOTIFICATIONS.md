# TASK-012: Сохранённые поиски и уведомления

> В `BACKEND_ROADMAP.md` это **TASK-028 «Push уведомления»** (через Telegram Bot API).
> Фронтенд: `FRONTEND-009-SAVED-SEARCHES.md`, `FRONTEND-010-NOTIFICATIONS.md`.

## Цель
Пользователь сохраняет поиск (район, цена, комнаты) и первым узнаёт о новых квартирах по нему,
а о квартирах из избранного — когда они дешевеют. Уведомления приходят в Telegram (бот)
и видны на странице уведомлений Mini App.

## Требования

### 1. База (миграция `saved_searches_notifications`)
- `bina_saved_searches`: `user_id`, `name`, `district_id`, `price_min`, `price_max`, `rooms`
  (4 = «4 и больше»), `notify`, `notify_since`, `last_viewed_at`.
- `bina_notifications`: `user_id`, `type` (`new_listing` / `price_drop` / `system`), `listing_id`,
  `search_id`, `old_price`, `new_price`, `text` (JSON, для `system`), `is_read`, `sent_at`.
  Частичные уникальные индексы: одно уведомление о новой квартире на пользователя и одно
  о снижении до конкретной цены — повторные запуски не создают дублей.
- `bina_listings.previous_price`, `price_changed_at`: парсер записывает прежнюю цену при её изменении.

### 2. Логика (`application/use_cases/notifications.py`)
- `CreateNotificationsUseCase`: для каждого поиска с `notify=True` — до 20 самых свежих активных
  квартир под фильтры, появившихся после `notify_since`; для избранного — квартиры, подешевевшие
  за 7 дней. Вставка через `ON CONFLICT DO NOTHING`.
- `DeliverNotificationsUseCase` + порт `INotificationSender`: отправка неотправленных
  (старые первыми). Итог отправки: `SENT`, `UNDELIVERABLE` (пользователь заблокировал бота —
  больше не пытаться), `RETRY` (сеть, лимиты — при следующем запуске). Уведомления старше
  2 дней в Telegram не отправляются, но остаются в Mini App.
- При включении `notify` поле `notify_since` сдвигается на «сейчас»: без пачки уведомлений
  о квартирах, появившихся, пока уведомления были выключены.

### 3. Telegram (`infrastructure/bot/notifications.py`)
«🏠 Новая квартира по поиску «Ваке, 2 комн.»» / «📉 Цена снижена: 1 800 ₾ → 1 500 ₾»,
заголовок, цена, комнаты, площадь и кнопка «Открыть»: квартира в Mini App (`BOT_MINI_APP_URL`)
или объявление на сайте-источнике. Языки ru и en (для ka — английский, как весь интерфейс бота).
Пауза 50 мс между сообщениями (лимит Telegram).

### 4. API
| Метод | Путь | Ответ |
|---|---|---|
| GET | `/api/searches` | `{items: SavedSearch[]}` с `new_count` |
| POST | `/api/searches` | 201; без `name` название из фильтров («Ваке, 2 комн., до 2 000 ₾»); 409 — больше 20; 422 |
| PATCH | `/api/searches/{id}` | `{name?, notify?}`; 404 — нет или чужой |
| POST | `/api/searches/{id}/viewed` | 204, обнуляет `new_count` |
| DELETE | `/api/searches/{id}` | 204 |
| GET | `/api/notifications?filter=all\|unread&page=&per_page=` | `{items, total, page, pages, unread_count}` |
| GET | `/api/notifications/unread-count` | `{count}` |
| POST | `/api/notifications/{id}/read` | 204; 404 — нет или чужое |
| POST | `/api/notifications/read-all` | 204 |

Все маршруты требуют `X-Telegram-Init-Data` (иначе 401). Формат ответов — как в задачах FRONTEND-009/010.

### 5. Запуск
```bash
bina-scrape notify     # создать и отправить уведомления вручную
bina-scrape schedule   # парсинг → перевод (если есть LLM_API_KEY) → уведомления
```
Для отправки в Telegram нужен `BOT_TOKEN` (без него уведомления создаются, но не отправляются),
для кнопки «Открыть» в Mini App — `BOT_MINI_APP_URL`.

### 6. Тесты
- `tests/integration/api/test_notifications_postgres.py`: CRUD поисков, чужие данные, полный сценарий
  (новая квартира, без дублей, `new_count`/`viewed`, снижение цены в избранном, отправка, API уведомлений),
  выключение и включение уведомлений.
- `tests/unit/bot/test_notifications_sender.py`: текст и кнопка, HTML-экранирование, языки, ошибки Telegram,
  пропуск устаревших, повтор временных ошибок.
- `tests/unit/infrastructure/scrapers/test_cli.py`: `notify`, уведомления в `schedule`.

## Definition of Done
1. ✅ Сохранённые поиски (API) и уведомления (API + Telegram)
2. ✅ Типы: новая квартира, снижение цены
3. ✅ Без дублей, устаревшие не отправляются, блокировка бота обрабатывается
4. ✅ Интеграция с автозапуском парсера
5. ✅ Тесты (unit + PostgreSQL), ruff и mypy для нового кода
6. ⏳ Настройка «Уведомления» в профиле Mini App (сейчас в `localStorage`) — подключить к серверу
