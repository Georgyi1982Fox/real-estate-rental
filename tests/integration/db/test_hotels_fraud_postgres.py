"""HotelsRepository: выбор непроверенных гостиниц, запись оценки, скрытие обмана (PostgreSQL)."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.models import Hotel
from bina.infrastructure.db.repositories.hotels import HotelFilters, HotelsRepository
from bina.infrastructure.db.repositories.users import UsersRepository


def _hotel(owner_id: object, name: str, **fields: object) -> Hotel:
    values: dict[str, object] = {
        "owner_user_id": owner_id,
        "kind": "hotel",
        "name": name,
        "city": "batumi",
        "amenities": [],
        "images": ["a.jpg"],
        "fraud_reasons": [],
        "description_ka": "",
        "description_ru": "Описание номера",
        "description_en": "",
        "min_price_gel": Decimal("100"),
        "max_guests": 2,
    }
    values.update(fields)
    return Hotel(**values)


async def test_list_fraud_unchecked_and_save(session: AsyncSession) -> None:
    hotels = HotelsRepository(session)
    owner = await UsersRepository(session).create(6001, "ru")
    fresh = _hotel(owner.id, "Fresh")
    checked = _hotel(owner.id, "Checked", checked_at=datetime.now(UTC))
    blank = _hotel(owner.id, "Blank", description_ru="")
    session.add_all([fresh, checked, blank])
    await session.flush()

    found = await hotels.list_fraud_unchecked(10)
    assert [h.id for h in found] == [fresh.id]

    await hotels.save_fraud(fresh.id, 15, [])
    await session.flush()
    await session.refresh(fresh)
    assert fresh.fraud_score == 15 and fresh.checked_at is not None
    # Проверенная больше не выбирается
    assert await hotels.list_fraud_unchecked(10) == []


async def test_high_fraud_score_hidden_from_search(session: AsyncSession) -> None:
    hotels = HotelsRepository(session)
    owner = await UsersRepository(session).create(6002, "ru")
    clean = _hotel(owner.id, "Clean")
    scam = _hotel(owner.id, "Scam", fraud_score=90)
    session.add_all([clean, scam])
    await session.flush()

    results, total = await hotels.search(HotelFilters(), "newest", 1, 20, datetime.now(UTC))

    ids = {h.id for h in results}
    assert clean.id in ids
    assert scam.id not in ids
    assert total == 1
