"""Интеграционные тесты бота на настоящем PostgreSQL (с pgvector).

Запуск: ``BINA_TEST_DATABASE_URL=postgresql+asyncpg://user@host:5432/bina_test pytest``.
Без переменной тесты пропускаются. **База очищается**: схема ``public``
пересоздаётся и заполняется миграцией ``initial_db_structure``.
"""

import importlib.util
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pgvector.sqlalchemy import Vector
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DATABASE_URL = os.getenv("BINA_TEST_DATABASE_URL")
MIGRATION = (
    Path(__file__).parents[3]
    / "src/bina/infrastructure/db/alembic/versions/initial_db_structure.py"
)

def _apply_migration(connection: Connection) -> None:
    spec = importlib.util.spec_from_file_location("initial_db_structure", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Обход бага миграции: в файле используется Vector без импорта.
    # Убрать, когда в миграцию добавят `from pgvector.sqlalchemy import Vector`.
    if not hasattr(module, "Vector"):
        setattr(module, "Vector", Vector)
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
        await connection.run_sync(_apply_migration)
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
