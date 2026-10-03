"""ListingsRepository на настоящем PostgreSQL."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.repositories.listings import ListingsRepository


async def test_add_skips_accepts_duplicate_ids(session: AsyncSession) -> None:
    """Одно объявление дважды в выдаче — не ошибка «cannot affect row a second time»."""
    repository = ListingsRepository(session)
    await repository.add_skips("ss", ["1", "2", "1"])
    await repository.add_skips("ss", ["2", "2"])
    await session.commit()
    since = datetime.now(UTC) - timedelta(minutes=1)
    assert await repository.recent_skips("ss", since) == {"1", "2"}
