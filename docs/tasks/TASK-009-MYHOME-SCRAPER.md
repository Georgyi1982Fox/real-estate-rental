# TASK-009: Парсер MyHome.ge (полный цикл до БД)

## Цель
Доделать парсер MyHome.ge: полные данные карточки (включая фото, телефон, имя
арендодателя) и реальное сохранение в БД, чтобы объявления появлялись в API и Mini App.

## Требования

### 1. Порт
Обновить src/bina/application/ports/scraper.py:
- RawListing: `photos` (все фото), `phone`, `owner_name`, `language` (язык текста: ru/ka)
- Новые поля необязательные: SS.ge-парсер продолжает работать без них

### 2. Модель и миграция
- Listing: колонки `url`, `phone`, `owner_name` (nullable); фото хранятся в `images`
- Миграция alembic `listing_contacts`

### 3. Парсер MyHome
Обновить src/bina/infrastructure/scrapers/myhome_scraper.py:
- Список объявлений с пагинацией (лимит, максимум страниц)
- Страница объявления: цена, район, комнаты, площадь, описание, все фото, телефон, имя
- Селекторы и URL поиска: в settings (без хардкода в коде парсера)
- Ошибка одной страницы или карточки не останавливает парсинг
  (пропуск, стоп после 3 ошибок подряд)
- Retry 3 попытки и rate limiting: уже есть в base_scraper.py
- `--dump-dir`: сохранить сырой HTML первой страницы списка и первой карточки
  (для обновления селекторов под реальный сайт)

### 4. Сохранение в БД
- ListingsRepository.create_or_update_from_raw: только существующие поля модели;
  текст в `title_ru`/`title_ka` по языку; фото, ссылка, телефон, имя
- Районы: поиск по ka/ru/en названию, создание с обязательными полями
- Одно битое объявление не откатывает остальные (savepoint)
- Embeddings: опционально (`--embeddings`), по умолчанию выключены
- Коммит в конце (раньше CLI не коммитил)

### 5. CLI
- `bina-scrape --source myhome --limit 100`
- `--source`: myhome | ss | all; `--no-details`; `--embeddings`; `--dump-dir PATH`
- `bina-scrape schedule --interval 6`: запуск по расписанию

### 6. Тесты
- Разбор HTML-фикстур: tests/unit/infrastructure/scrapers/test_data/
  (myhome_test.html: список, myhome_detail_test.html: карточка)
- Пагинация, пропуск ошибок, dump (HTTP замокан)
- Сохранение в PostgreSQL (интеграционный тест)

## Реальный сайт (сентябрь 2026)
- URL поиска: `/ru/nedvizhimost/arenda/kvartira/tbilisi/?deal_types=2&real_estate_types=1&currency_id=1&cities=1&page={page}`
  (старый `/ru/search?AjaxSearchFieldForm...` отвечает 404).
- Сайт на Next.js: 24 объявления на странице лежат JSON-ом в `<script id="__NEXT_DATA__">`.
  Парсер читает его в первую очередь (`_parse_listings`, `_parse_detail`), разбор HTML по
  селекторам остался запасным вариантом.
- Поля JSON: `id`, `dynamic_title`, `comment`, `price["1"].price_total` (лари; `"2"` доллары,
  `"3"` евро), `room`, `area`, `urban_name`, `images[].large` (`is_main` первым), `user_title`.
  Ссылка на объявление: `/ru/nedvizhimost/{dynamic_slug}-{id}/`.
- Страница объявления: тот же JSON (`statement`) плюс `owner_name` и полное `comment`.
  Телефон сайт отдаёт замаскированным (`user_phone_number: "591589***"`), полный номер
  только по кнопке. Замаскированные номера не сохраняются, поэтому `phone` пока пустой.
- Фикстура `test_data/myhome_next_list.html`: урезанная копия настоящей страницы (2 объявления).

## Definition of Done
1. `bina-scrape --source myhome --limit 100` сохраняет объявления в БД
2. Объявления видны в /api/listings и Mini App (с фото)
3. Телефон и имя сохраняются, если есть на странице
4. Ошибки сайта не роняют парсинг
5. Тесты проходят, ruff и mypy для нового кода
6. Показать список файлов
