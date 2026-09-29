"""Одна квартира на двух сайтах показывается один раз (TASK-090), на PostgreSQL."""

import dataclasses
from typing import Any

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.application.use_cases.find_duplicates import FindDuplicatesUseCase
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import ListingStatus
from bina.infrastructure.db.repositories.listings import ListingsRepository


def flat(source: str, source_id: str, **fields: Any) -> RawListing:
    base = RawListing(
        source_id=source_id,
        source_name=source,
        title=f"Квартира {source_id}",
        description="Описание",
        price=1500.0,
        currency="GEL",
        rooms=2,
        area=60.0,
        district="Ваке",
        url=f"https://{source}.example/{source_id}",
        photos=[f"https://img.example/{source_id}.jpg"],
        has_details=True,
        floor=5,
        total_floors=9,
        latitude=41.7100,
        longitude=44.7700,
    )
    return dataclasses.replace(base, **fields)


async def save(session: AsyncSession, raw: RawListing) -> None:
    # Отдельные транзакции: разное created_at, основное — появившееся раньше
    await ListingsRepository(session).create_or_update_from_raw(raw)
    await session.commit()


async def find(session: AsyncSession) -> tuple[int, int]:
    stats = await FindDuplicatesUseCase(ListingsRepository(session)).execute(100)
    await session.commit()
    return stats.checked, stats.found


async def test_same_apartment_shown_once(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await save(session, flat("ss", "A"))
    await save(session, flat("myhome", "B", price=1480.0, area=61.0, latitude=41.7104))
    await save(session, flat("myhome", "C", floor=7))  # тот же дом, другой этаж
    await save(session, flat("ss", "D", title="Квартира D"))  # повтор на том же сайте

    assert await find(session) == (4, 2)
    assert await find(session) == (0, 0), "проверенные не проверяются снова"

    repository = ListingsRepository(session)
    a = await repository.find_by_source("A", "ss")
    b = await repository.find_by_source("B", "myhome")
    d = await repository.find_by_source("D", "ss")
    assert a is not None and b is not None and d is not None
    assert (a.duplicate_of, b.duplicate_of, d.duplicate_of) == (None, a.id, a.id)

    app = create_app(ApiSettings(), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        items = (await client.get("/api/listings")).json()["items"]
        assert sorted(item["source_url"] for item in items) == [
            "https://myhome.example/C",
            "https://ss.example/A",
        ]
        detail = (await client.get(f"/api/listings/{a.id}")).json()
        assert detail["also_on"] == [
            {"source": "myhome", "url": "https://myhome.example/B"},
            {"source": "ss", "url": "https://ss.example/D"},
        ]
        # Дубликат открывается по ссылке (из уведомления) и ведёт на основное
        from_b = (await client.get(f"/api/listings/{b.id}")).json()
        assert {link["url"] for link in from_b["also_on"]} == {
            "https://ss.example/A",
            "https://ss.example/D",
        }

        # Скрытые дубликаты не переводятся
        untranslated = await repository.list_untranslated(10)
        assert b.id not in {listing.id for listing in untranslated}

        # Основное сняли с сайта — показываются дубликаты
        a.status = ListingStatus.ARCHIVED
        await session.commit()
        items = (await client.get("/api/listings")).json()["items"]
        assert sorted(item["source_url"] for item in items) == [
            "https://myhome.example/B",
            "https://myhome.example/C",
            "https://ss.example/D",
        ]


async def test_price_change_rechecks(session: AsyncSession) -> None:
    await save(session, flat("ss", "A"))
    await save(session, flat("myhome", "B", price=2500.0))
    assert await find(session) == (2, 0)

    # Цену на MyHome поправили — это та же квартира
    await save(session, flat("myhome", "B", price=1500.0))
    assert await find(session) == (1, 1)
