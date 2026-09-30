# TASK-104 + TASK-080: Информация о районе и место квартиры на карте

## Справка по району (TASK-104)
`GET /api/districts/{id}` — на языке пользователя, цены в лари:
```json
{"id": "…", "name": "Ваке", "names": {"ka": "ვაკე", "ru": "Ваке", "en": "Vake"},
 "latitude": 41.709, "longitude": 44.758, "distance_km": 4.0, "minutes_to_center": 15,
 "metro": false,
 "tags": [{"code": "premium", "title": "Престижный"}, {"code": "green", "title": "Парки и зелень"}],
 "about": "Престижный район с Ваке-парком, кафе и ресторанами на проспекте Чавчавадзе.",
 "listings": 42, "currency": "GEL",
 "median_rent": [{"rooms": 1, "price": 1100}, {"rooms": 2, "price": 1650}],
 "median_per_m2": 24.5, "note": "Цены — медиана по объявлениям…"}
```
- **Статичная справка** (`application/district_guide.py`): 30 районов Тбилиси — примерный центр,
  есть ли метро, 1-3 метки характера (центр, зелень, тихий, кафе, исторический, новостройки,
  доступные цены, престижный, университеты), короткое описание на ka/ru/en у 17 главных.
- **Время до центра** — оценка по прямой до площади Свободы (+30% на дороги, 20 км/ч).
- **Цены** — медиана по объявлениям, которые сейчас в поиске (без скрытых дублей и
  мошеннических); доллары и евро переводятся в лари. Медиана по комнатам показывается, только
  если объявлений не меньше 5 (`4` = «4 и больше»).
- Района нет в справке — координаты, метро, метки и описание будут `null` / пустыми.

## Место на карте (TASK-080)
`GET /api/listings/{id}/location`:
```json
{"precision": "exact", "latitude": 41.7101, "longitude": 44.7612, "district": "Ваке",
 "address": "Paliashvili 1",
 "links": {"google": "https://www.google.com/maps/search/?api=1&query=…",
           "yandex": "https://yandex.com/maps/?ll=…&pt=…", "osm": "https://www.openstreetmap.org/?…"}}
```
- `exact` — точка из объявления (SS.ge, MyHome.ge) или найденная по адресу;
- `district` — точного места нет: центр района, на карте подписать «примерно»;
- `none` — неизвестно (карту не показывать).

### Поиск по адресу
У объявлений из Telegram-каналов есть только адрес. Раз в час (после склейки дублей) парсер
ищет до 30 таких адресов через **OpenStreetMap Nominatim** — бесплатно, без ключа, не чаще
1 запроса в секунду, только в пределах Тбилиси. Не нашли — отмечаем (`geocoded_at`) и больше
не ищем; карта покажет центр района. Сервис не ответил — попробуем в следующий раз.

Вручную: `docker compose exec scraper bina-scrape geocode --limit 30`
(вывод: `карта: проверено адресов N, на карте N, ошибок N`).

Миграция `listing_geocoded` (колонка `geocoded_at`) применяется сама при `update-bina.bat`.

## Код
`application/district_guide.py`, `application/ports/geocoder.py`,
`application/use_cases/geocode_listings.py`, `infrastructure/geo/nominatim.py`,
`ListingsRepository.district_stats / to_geocode / save_location`,
`infrastructure/api/routes/districts.py`, `infrastructure/api/routes/location.py`.

## Фронтенд
`FRONTEND-026-DISTRICT-MAP.md` (не выдана).
