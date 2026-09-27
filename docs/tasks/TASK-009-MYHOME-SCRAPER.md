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

## Ограничение
Фикстуры и селекторы по умолчанию синтетические: из контейнера разработки нет доступа
к myhome.ge. Реальные селекторы обновляются по HTML, сохранённому командой
`bina-scrape --source myhome --limit 2 --dump-dir scraped_html` на машине с доступом к сайту.

## Definition of Done
1. `bina-scrape --source myhome --limit 100` сохраняет объявления в БД
2. Объявления видны в /api/listings и Mini App (с фото)
3. Телефон и имя сохраняются, если есть на странице
4. Ошибки сайта не роняют парсинг
5. Тесты проходят, ruff и mypy для нового кода
6. Показать список файлов
