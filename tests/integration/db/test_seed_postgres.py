"""Загрузка демо-данных на настоящем PostgreSQL."""

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.models import District, Listing
from bina.infrastructure.db.seed import DEMO_SOURCE, delete_demo_data, load_demo_data

MOCK_FILE = Path(__file__).parents[3] / "frontend" / "mock_data.json"


async def count(session: AsyncSession, model: type[District] | type[Listing]) -> int:
    return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


async def test_load_frontend_mock_data(session: AsyncSession) -> None:
    data = json.loads(MOCK_FILE.read_text(encoding="utf-8"))

    first = await load_demo_data(session, data)
    await session.commit()
    second = await load_demo_data(session, data)
    await session.commit()

    assert (first.districts_created, first.listings_created) == (len(data["districts"]), 12)
    assert (second.districts_created, second.listings_created, second.listings_updated) == (
        0,
        0,
        12,
    )
    assert await count(session, Listing) == 12
    listing = (
        await session.execute(select(Listing).where(Listing.source_id == f"{DEMO_SOURCE}-1"))
    ).scalar_one()
    assert listing.title_ru == "Уютная квартира в Сабуртало"
    assert listing.title_ka == "მყუდრო ბინა საბურთალოზე"


async def test_reuses_existing_district_and_resets(session: AsyncSession) -> None:
    data = {
        "districts": [{"id": "vake", "name": {"ka": "ვაკე", "ru": "Ваке", "en": "Vake"}}],
        "listings": [
            {"id": 1, "title": {"ru": "А", "ka": "ა"}, "price": 1000, "rooms": 2, "area": 50,
             "district": "vake"},
        ],
    }
    await load_demo_data(session, data)
    await session.commit()
    await load_demo_data(session, data)
    assert await count(session, District) == 1

    assert await delete_demo_data(session) == 1
    await session.commit()
    assert await count(session, Listing) == 0
    assert await count(session, District) == 1


async def test_unknown_district_is_rejected(session: AsyncSession) -> None:
    data = {
        "districts": [],
        "listings": [{"id": 1, "title": "x", "price": 1, "rooms": 1, "area": 1, "district": "?"}],
    }
    with pytest.raises(ValueError, match="unknown district"):
        await load_demo_data(session, data)
