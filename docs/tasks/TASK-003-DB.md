# TASK-003: Ядро базы данных PostgreSQL

## Контекст
Проект Bina.ai. Стек: Python 3.12+, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16 + pgvector, Alembic.

## Цель
Создать архитектуру БД, настроить Alembic, написать SQLAlchemy-модели для ядра системы.

## Требования

### 1. Alembic
- Настроить alembic для async SQLAlchemy (asyncpg)
- Создать структуру в src/bina/infrastructure/db/alembic/
- Настроить env.py с run_async()

### 2. Базовые модели
Создать Base с миксинами:
- TimestampMixin (created_at, updated_at)
- SoftDeleteMixin (is_deleted, deleted_at)
- Префикс таблиц: bina_

### 3. Модели (создать в src/bina/infrastructure/db/models/)

**Users (bina_users)**
- id (UUID, pk)
- telegram_id (BigInteger, unique, index)
- language (String(3), default='ru')
- role (Enum: user, realtor, admin)
- balance (Numeric(10,2), default=0)
- subscription_tier (Enum: free, nomad, family, realtor)
- subscription_expires_at (DateTime, nullable)

**Districts (bina_districts)**
- id (UUID, pk)
- name_ru, name_ka, name_en (String)
- center_coordinates (String, nullable)
- avg_price_per_m2 (Numeric)
- safety_score (Integer)
- infrastructure_json (JSONB)

**Listings (bina_listings)**
- id (UUID, pk)
- source_id (String, unique)
- source_name (String)
- title_ru, title_ka (String)
- description_ru, description_ka (Text)
- price (Numeric)
- currency (String, default='GEL')
- district_id (FK -> bina_districts.id)
- rooms (Integer)
- area (Numeric)
- is_verified (Boolean, default=False)
- fraud_score (Integer, default=0)
- status (Enum: active, sold, archived)

**Embeddings (bina_embeddings)**
- id (UUID, pk)
- listing_id (FK -> bina_listings.id)
- vector (Vector(1536)) -- pgvector
- model_name (String, default='text-embedding-3-small')
- Индекс HNSW на vector

**Favorites (bina_favorites)**
- user_id (FK)
- listing_id (FK)
- created_at
- Уникальный индекс (user_id, listing_id)

**Payments (bina_payments)**
- id (UUID, pk)
- user_id (FK)
- amount (Numeric)
- currency (String)
- provider (Enum: telegram_stars, stripe)
- provider_payment_id (String, unique)
- status (Enum: pending, success, failed)
- created_at

### 4. Индексы
- Составные индексы для listings (district_id + status + price)
- GIN индекс для полнотекстового поиска (tsvector)
- Комментарий с EXPLAIN ANALYZE к миграции

### 5. Репозитории
Создать IListingsRepository (порт) и его реализацию.
Метод: get_active_listings_by_district(district_id: UUID, limit: int) -> List[Listing]

## Definition of Done
1. alembic revision --autogenerate работает
2. Код проходит ruff check и mypy --strict
3. В ответе перечислить все созданные файлы и SQL для HNSW индекса

## Запреты
- SELECT * в репозиториях
- Синхронные вызовы БД
- Хардкод DATABASE_URL