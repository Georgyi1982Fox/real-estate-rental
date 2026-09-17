import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.bina.infrastructure.db.models import Base


class DatabaseManager:
    """Менеджер базы данных."""
    
    def __init__(self) -> None:
        self._engine = create_async_engine(
            os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/bina"),
            echo=False,
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=30,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    
    async def create_all(self) -> None:
        """Создать все таблицы."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_all(self) -> None:
        """Удалить все таблицы."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Генератор сессий."""
        async with self._session_factory() as session:
            yield session