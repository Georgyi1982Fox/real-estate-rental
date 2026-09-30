"""Напоминания об оплате аренды (TASK-109): репозиторий на настоящем PostgreSQL."""

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.repositories.rent_reminders import RentRemindersRepository
from bina.infrastructure.db.repositories.users import UsersRepository

TODAY = date(2026, 10, 2)


async def test_repository(session: AsyncSession) -> None:
    user = await UsersRepository(session).create(501, "en")
    other = await UsersRepository(session).create(502, "ru")
    repository = RentRemindersRepository(session)
    first = await repository.add(user.id, 5, Decimal(1500), "GEL")
    first_id = first.id
    await repository.add(user.id, 20, Decimal(700), "USD")
    await session.commit()

    assert [r.day for r in await repository.list_for_user(user.id)] == [5, 20]
    assert await repository.count_for_user(user.id) == 2

    due = await repository.not_reminded_today(TODAY)
    assert {(r.day, r.telegram_id, r.language) for r in due} == {(5, 501, "en"), (20, 501, "en")}

    await repository.mark_reminded(first_id, TODAY)
    await session.commit()
    assert [r.day for r in await repository.not_reminded_today(TODAY)] == [20]
    assert len(await repository.not_reminded_today(date(2026, 10, 3))) == 2

    # Чужое не отмечается и не удаляется
    assert not await repository.mark_paid(other.id, first_id, date(2026, 10, 5))
    assert not await repository.delete(other.id, first_id)
    assert await repository.mark_paid(user.id, first_id, date(2026, 10, 5))
    await session.commit()
    [paid] = [r for r in await repository.not_reminded_today(date(2026, 10, 3)) if r.day == 5]
    assert paid.paid_for == date(2026, 10, 5)

    assert await repository.delete(user.id, first_id)
    await session.commit()
    assert await repository.count_for_user(user.id) == 1
