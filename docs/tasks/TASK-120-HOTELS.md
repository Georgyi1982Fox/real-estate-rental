# TASK-120: Раздел «Гостиницы»

## Идея
Отдельный раздел для гостиниц, гостевых домов, хостелов и апарт-отелей. С сайтов ничего
не собирается — объекты размещают сами люди: хозяева, риэлторы, любой пользователь.
С квартирами в поиске не смешивается. Владелец сервиса в модерации не участвует:
проверяют правила (а на этапе 2 — ИИ) и жалобы.

Решения владельца (9 октября 2026):
- связь — чат и звонок (кнопки «Позвонить», WhatsApp, Telegram; чат с переводом в боте —
  этап 2), онлайн-бронирования пока нет;
- размещение бесплатное, платный «🔥 Топ» (этап 2);
- объект в поиске сразу после автоматической проверки.

## Этап 1 (готово)
- Таблицы `bina_hotels`, `bina_hotel_rooms`, `bina_hotel_complaints` (миграция `hotels`).
- Объект: тип (`hotel`, `guesthouse`, `hostel`, `apart_hotel`), название, город, адрес,
  точка на карте, звёзды, удобства (коды — `application/hotels.py` `AMENITIES`),
  время заезда/выезда, описание (в колонку своего языка), фото (до 20), телефон,
  WhatsApp, Telegram хозяина.
- Номера: тип (`single`, `double`, `twin`, `triple`, `family`, `suite`, `dorm`), гостей,
  цена за ночь (GEL/USD/EUR), сколько таких номеров. Цена «от» в лари и вместимость
  считаются сами (`min_price_gel`, `max_guests`) — по ним поиск и сортировка.
- Проверка правилами при размещении и изменении (`problems`): ссылки и контакты в тексте,
  слишком короткое описание, странное название, цена ночи не 10–5000 ₾.
- Лимиты: 5 включённых объектов на человека, 5 новых в сутки, 30 типов номеров.
- Жалобы — как на квартиры: от 3 человек (аккаунты старше суток) объект скрыт;
  оплаченные и проверенные сами не скрываются.
- Владельцу сервиса в Telegram — сообщение о новом объекте с кнопкой «Скрыть».
- Объект без номеров (нет цены) в поиск не попадает.

### API
Гостям:
- `GET /api/hotels/options` — коды типов, номеров, удобств, сортировок, лимиты;
- `GET /api/hotels?city=&kind=&guests=&price_min=&price_max=&stars=&amenities=&sort=&page=&per_page=`
  — `sort`: `newest`, `price_asc`, `price_desc`, `stars_desc`; «🔥 Топ» всегда сверху;
- `GET /api/hotels/{id}` — объект с номерами (`description` — какие языки есть);
- `GET /api/hotels/{id}/contact` — телефон, `whatsapp_url`, `telegram_url` (нужен вход);
- `POST /api/hotels/{id}/complaints` — `{"reason", "comment"}` (причины — как у квартир).

Хозяину (`/api/my/hotels`):
- `GET` — свои (`status`: active / off / hidden), `limit`;
- `POST` — разместить (тело — `HotelIn` с `rooms`); 409 — уже 5 включённых, 429 — 5 новых
  за сутки, 422 `rejected: <коды>` — не прошёл проверку;
- `GET/PUT/DELETE /{id}`, `PATCH /{id}` `{"active": bool}`;
- `POST /{id}/photos` (тело — файл), `DELETE /{id}/photos/{index}`;
- `POST /{id}/rooms`, `PUT /{id}/rooms/{room_id}`, `DELETE /{id}/rooms/{room_id}`.

## Этап 2
- ✅ Проверка ИИ (спам, чужие фото, обман) и автоперевод описаний на ka/ru/en.
- ✅ «🔥 Топ» за Telegram Stars (как у квартир): 7 дней первым в разделе, повторная
  оплата продлевает. Цена — `HOTEL_PROMOTION_PRICE_STARS` в `.env` (по умолчанию 150).
  Счёт `htop:<id>` создаёт мини-приложение, оплату принимает бот.
- ✅ Раздел «🏨 Гостиницы» в меню бота и `/hotels`: до 8 объектов кнопками (сначала «Топ»),
  «Все гостиницы» и «Мои гостиницы» — в приложении.
- ✅ Карточка гостиницы в боте (кнопка в разделе или ссылка `start=h_<id>`): фото, цена «от»,
  гостей, заезд/выезд, начало описания на языке пользователя; «📞 Контакты» (телефон,
  WhatsApp, Telegram — только по нажатию), «Подробнее в приложении», «Поделиться».
- ✅ Чат с хозяином гостиницы в боте с переводом: «✍️ Написать хозяину» в карточке →
  сообщение уходит хозяину на его языке (оригинал — мелко), под ним «↩️ Ответить»; гостю под
  ответом — «↩️ Ответить» и «🏨 Открыть гостиницу». Telegram друг друга не видно. Тот же
  диалог `bina_conversations` (миграция `hotel_chat`: `hotel_id` вместо `listing_id`) и тот
  же лимит — 5 новых диалогов в сутки на квартиры и гостиницы вместе.
- ✅ «Мои данные»: свои гостиницы (с номерами) и жалобы на гостиницы — в выгрузке;
  при удалении аккаунта гостиницы удаляются целиком вместе с фото и перепиской.
- Позже: даты и заявки на бронирование, отзывы.

### API этапа 2
- `GET /api/hotels/options` — ещё `promotion_price_stars`, `promotion_days`;
- `GET /api/my/hotels`, `GET /api/my/hotels/{id}` — ещё `promoted_until`;
- `GET /api/hotels/{id}/share?lang=` → `{url, text, telegram_url}` — ссылка на карточку
  гостиницы в боте (`start=h_<id>`): для «📤 Поделиться» и «💬 Написать хозяину в боте»;
  404 — объекта нет в разделе, 503 — бот не настроен;
- `POST /api/my/hotels/{id}/promotion` → `{url, price_stars, days}` — счёт для
  `Telegram.WebApp.openInvoice`; 404 — не свой, 409 — объект не в разделе (снят, скрыт,
  нет цены), 503 — нет токена бота.

## Код
`application/hotels.py`, `application/use_cases/hotels.py`,
`application/hotel_promotion.py`, `application/use_cases/hotel_promotion.py`,
`infrastructure/db/models/hotels.py`, `infrastructure/db/repositories/hotels.py`,
`infrastructure/api/routes/hotels.py`, `infrastructure/payments/invoice.py`,
`infrastructure/bot/hotel_alerts.py`, `infrastructure/bot/handlers/hotels.py`,
чат — `application/use_cases/chat.py`, `infrastructure/bot/handlers/chat.py`.
