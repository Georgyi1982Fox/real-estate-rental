"""Интеграционные тесты на настоящем PostgreSQL (с pgvector).

Запуск: ``BINA_TEST_DATABASE_URL=postgresql+asyncpg://user@host:5432/bina_test pytest``.
Без переменной тесты пропускаются. **База очищается**: схема ``public``
пересоздаётся и заполняется миграциями из ``alembic/versions``.
"""

import importlib.util
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DATABASE_URL = os.getenv("BINA_TEST_DATABASE_URL")
VERSIONS = Path(__file__).parents[2] / "src/bina/infrastructure/db/alembic/versions"
# Порядок применения миграций (down_revision → revision)
MIGRATIONS = (
    "initial_db_structure",
    "listing_images",
    "listing_contacts",
    "listing_translations_en",
    "saved_searches_notifications",
    "listing_search_vector",
    "payments_plan",
    "listing_fraud",
    "saved_search_districts",
    "listing_details",
    "district_names",
    "text_languages",
    "clean_html_texts",
    "listing_checked_at",
    "saved_search_details",
    "listing_duplicates",
    "scrape_skips",
    "ai_usage",
    "listing_geocoded",
    "complaints",
    "premium_reminders",
    "timestamp_columns",
    "referrals",
    "rent_reminders",
    "district_city",
    "embeddings_unique",
    "listing_rent_period",
)


def _apply_migrations(connection: Connection) -> None:
    for name in MIGRATIONS:
        spec = importlib.util.spec_from_file_location(name, VERSIONS / f"{name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Движок на чистой базе со схемой из миграции."""
    if not DATABASE_URL:
        pytest.skip("BINA_TEST_DATABASE_URL is not set")
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(_apply_migrations)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Фабрика сессий, как в :class:`DatabaseManager`."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Сессия для подготовки данных и проверок."""
    async with session_factory() as session:
        yield session
