# TASK-006: Парсер объявлений недвижимости

## Контекст
Проект Bina.ai. Нужно собирать объявления с MyHome.ge и SS.ge.
Стек: Python 3.12+, httpx, BeautifulSoup4, APScheduler.

## Цель
Создать систему парсинга объявлений с автообновлением.

## Требования

### 1. Интерфейс
Создать src/bina/application/ports/scraper.py:
- Класс BaseScraper (ABC)
- Метод scrape_listings(limit: int) -> List[RawListing]
- Dataclass RawListing (source_id, source_name, title, description, price, currency, rooms, area, district, url, photos)

### 2. Парсер MyHome.ge
Создать src/bina/infrastructure/scrapers/myhome_scraper.py:
- Парсинг через BeautifulSoup4
- Извлечение: заголовок, цена, район, комнаты, площадь, фото, описание
- Пагинация
- Rate limiting (1-2 сек между запросами)
- User-Agent ротация

### 3. Парсер SS.ge
Создать src/bina/infrastructure/scrapers/ss_scraper.py:
- Аналогичная структура
- Адаптация селекторов под SS.ge

### 4. Нормализация
Создать src/bina/infrastructure/scrapers/normalizer.py:
- Цены к GEL
- Очистка текста
- Маппинг районов на bina_districts
- Валидация полей

### 5. Дедупликация
Создать src/bina/infrastructure/scrapers/deduplicator.py:
- Проверка по source_id + source_name
- Обновление если изменилась цена
- Логирование дубликатов

### 6. Планировщик
Создать src/bina/infrastructure/scrapers/scheduler.py:
- APScheduler, интервал 6 часов
- Ручной запуск через CLI
- Логирование

### 7. Сохранение в БД
Создать src/bina/infrastructure/scrapers/repository.py:
- RawListing → Listing модель
- Создание embeddings через LLM Gateway
- Обновление статистики районов

### 8. CLI
Добавить в pyproject.toml:
- bina-scrape myhome
- bina-scrape ss
- bina-scrape all
- bina-scrape schedule

### 9. Конфиг
В settings добавить:
- SCRAPE_INTERVAL_HOURS=6
- SCRAPE_DELAY_SECONDS=2
- SCRAPE_USER_AGENTS (список)

## Definition of Done
1. Парсеры MyHome и SS работают
2. Нормализация и дедупликация работают
3. Планировщик запускается
4. Данные сохраняются в БД
5. ruff и mypy проходят
6. Список файлов в ответе

## Запреты
- Синхронные HTTP запросы
- Хардкод URL и селекторов
- Парсинг без rate limiting
- Дубликаты в БД