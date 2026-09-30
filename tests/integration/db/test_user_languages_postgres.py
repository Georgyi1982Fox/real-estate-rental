"""Язык владельцев для сообщений о сбоях (TASK-043)."""

from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.repositories.users import UsersRepository


async def test_languages_by_telegram_ids(session: AsyncSession) -> None:
    repository = UsersRepository(session)
    await repository.create(11, "ka")
    await repository.create(12, "en")
    await session.commit()
    assert await repository.languages_by_telegram_ids([11, 12, 13]) == {11: "ka", 12: "en"}
