"""Подробности объявлений на настоящем PostgreSQL (TASK-018).

Сохранение со страницы объявления, защита от затирания данными из списка,
новые фильтры и сортировка «новые сверху» по дате сайта, описания от сайта на
других языках, дозагрузка подробностей и архив снятых объявлений.
"""

import dataclasses
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.application.ports.translator import ListingText
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import ListingStatus
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.scrapers.backfill import backfill_details
from bina.infrastructure.scrapers.ss_scraper import SSScraper

NOW = datetime.now(UTC).replace(microsecond=0)
SS_DETAIL = Path("tests/unit/infrastructure/scrapers/test_data/ss_detail.html")


def raw(source_id: str, **fields: Any) -> RawListing:
    base = RawListing(
        source_id=source_id,
        source_name="ss",
        title=f"Квартира {source_id}",
        description="Полное описание",
        price=1500.0,
        currency="GEL",
        rooms=2,
        area=60.0,
        district="Ваке",
        url=f"https://home.ss.ge/ru/{source_id}",
        photos=[f"https://static.ss.ge/{source_id}.jpg"],
    )
    return dataclasses.replace(base, **fields)


def detailed(source_id: str, **fields: Any) -> RawListing:
    values: dict[str, Any] = {
        "has_details": True,
        "floor": 3,
        "total_floors": 9,
        "bedrooms": 1,
        "bathrooms": 1,
        "features": ["furniture", "air_conditioning"],
        "condition": "newly_renovated",
        "owner_type": "owner",
        "address": "ул. Мачабели 6",
        "published_at": NOW - timedelta(days=3),
        "updated_at": NOW - timedelta(days=1),
    }
    values.update(fields)
    return raw(source_id, **values)


async def ids(client: AsyncClient, query: str = "") -> list[str]:
    body = (await client.get(f"/api/listings?per_page=50&{query}")).json()
    assert "items" in body, body
    return [item["title"]["ru"].removeprefix("Квартира ") for item in body["items"]]


async def test_details_filters_and_sort(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    repository = ListingsRepository(session)
    await repository.create_or_update_from_raw(detailed("a"))
    await repository.create_or_update_from_raw(
        detailed(
            "b",
            floor=9,
            features=["furniture", "air_conditioning", "washing_machine", "bogus"],
            owner_type="agent",
            condition="renovated",
            updated_at=NOW - timedelta(hours=1),
        )
    )
    await repository.create_or_update_from_raw(
        detailed("c", floor=1, bathrooms=2, published_at=NOW - timedelta(days=40), updated_at=None)
    )
    # created_at = начало транзакции: «d» в отдельной транзакции, чтобы быть позже «c»
    await session.commit()
    await repository.create_or_update_from_raw(raw("d"))  # без подробностей, свежий у нас
    await session.commit()

    app = create_app(ApiSettings(), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # «Новые сверху» — по дате обновления на сайте; у «c» и «d» её нет — дата у нас
        assert await ids(client) == ["d", "c", "b", "a"]

        assert await ids(client, "features=furniture,washing_machine") == ["b"]
        assert await ids(client, "features=furniture") == ["c", "b", "a"]
        assert await ids(client, "not_first_floor=true&not_last_floor=true") == ["a"]
        assert await ids(client, "floor_min=2&floor_max=5") == ["a"]
        assert await ids(client, "bathrooms=2") == ["c"]
        assert await ids(client, "owner_only=true") == ["c", "a"]
        assert await ids(client, "condition=renovated,white_frame") == ["b"]
        assert set(await ids(client, "published_days=7")) == {"a", "b", "d"}
        assert (await client.get("/api/listings?features=wings")).status_code == 422

        body = (await client.get("/api/listings?features=washing_machine")).json()["items"][0]
        # Коды в постоянном порядке, неизвестные отброшены
        assert body["features"] == ["furniture", "air_conditioning", "washing_machine"]
        assert (body["floor"], body["total_floors"], body["owner_type"]) == (9, 9, "agent")
        assert body["address"] == "ул. Мачабели 6"
        updated = datetime.fromisoformat(body["updated_at"].replace("Z", "+00:00"))
        assert updated == NOW - timedelta(hours=1)


async def test_list_only_update_keeps_details(session: AsyncSession) -> None:
    repository = ListingsRepository(session)
    full = "Очень подробное описание квартиры. " * 20
    await repository.create_or_update_from_raw(
        detailed(
            "x",
            description=full,
            descriptions={"ka": "ქართული აღწერა", "en": "English description"},
            phone="595000000",
        )
    )
    await session.commit()

    # Следующий запуск: страница объявления не загрузилась, есть только список
    listing = await repository.create_or_update_from_raw(
        raw("x", description="Очень подробное…", photos=[], features=["furniture"])
    )
    await session.commit()

    assert listing.description_ru == full
    assert (listing.description_ka, listing.description_en) == (
        "ქართული აღწერა",
        "English description",
    )
    assert listing.features == ["furniture", "air_conditioning"]
    assert (listing.floor, listing.phone, listing.images) == (
        3,
        "595000000",
        ["https://static.ss.ge/x.jpg"],
    )
    assert listing.fraud_checked_at is None  # не проверялось; сброса из-за списка не было

    # Перевод не затирает описания, которые сайт дал сам, но добавляет заголовки
    await repository.save_texts(
        listing.id,
        {
            "ka": ListingText("ბინა x", "AI ka"),
            "en": ListingText("Apartment x", "AI en"),
        },
    )
    await session.commit()
    await session.refresh(listing)
    assert (listing.title_ka, listing.description_ka) == ("ბინა x", "ქართული აღწერა")
    assert (listing.title_en, listing.description_en) == ("Apartment x", "English description")


class FakeSite(SSScraper):
    """SS без сети: страница объявления из фикстуры, «gone» — 404."""

    def __init__(self) -> None:
        super().__init__(delay_seconds=0)
        self.requested: list[str] = []

    async def _fetch_page(self, url: str) -> str:
        self.requested.append(url)
        if url.endswith("gone"):
            request = httpx.Request("GET", url)
            raise httpx.HTTPStatusError(
                "404", request=request, response=httpx.Response(404, request=request)
            )
        return SS_DETAIL.read_text(encoding="utf-8")


async def test_backfill_details(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    repository = ListingsRepository(session)
    await repository.create_or_update_from_raw(
        raw("36583130", description="Сдается комфортная… (обрезано)")
    )
    await repository.create_or_update_from_raw(raw("gone"))
    await repository.create_or_update_from_raw(detailed("done"))
    await session.commit()

    site = FakeSite()
    stats = await backfill_details(session_factory, {"ss": site}, limit=10)

    assert (stats.checked, stats.updated, stats.archived, stats.failed) == (2, 1, 1, 0)
    assert not any(url.endswith("done") for url in site.requested)

    session.expire_all()
    filled = await repository.find_by_source("36583130", "ss")
    gone = await repository.find_by_source("gone", "ss")
    assert filled is not None and gone is not None
    assert filled.details_fetched_at is not None
    assert filled.description_ru.startswith("Сдается комфортная, отремонтированная")
    assert filled.description_ka.startswith("ქირავდება")
    assert "washing_machine" in filled.features
    assert filled.phone == "595000000"
    assert gone.status == ListingStatus.ARCHIVED

    # Второй запуск: делать больше нечего
    again = await backfill_details(session_factory, {"ss": FakeSite()}, limit=10)
    assert again.checked == 0
