"""Advisory lock PostgreSQL: одна задача за раз во всех процессах."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Ключи блокировок (любые уникальные числа bigint)
TRANSLATE_LOCK = 710_001
FRAUD_LOCK = 710_002


@asynccontextmanager
async def advisory_lock(engine: AsyncEngine, key: int) -> AsyncIterator[bool]:
    """Пытается взять блокировку, не дожидаясь её; ``False`` — уже занята другим процессом.

    Блокировка живёт на отдельном соединении и снимается при выходе
    (или сама, если процесс упал и соединение закрылось).
    """
    async with engine.connect() as connection:
        acquired = bool(
            (
                await connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
            ).scalar()
        )
        await connection.commit()
        try:
            yield acquired
        finally:
            if acquired:
                await connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                await connection.commit()
