"""Полный цикл парсинга на настоящем PostgreSQL: сохранение, районы, повторный запуск."""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import BaseScraper, NeedsDetails, RawListing
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import District, Listing, ListingStatus
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.scrapers.pipeline import run_scrape


def raw(source_id: str, **overrides: object) -> RawListing:
    values: dict[str, object] = {
        "source_id": source_id,
        "source_name": "myhome",
        "title": f"Квартира {source_id}",
        "description": "Описание",
        "price": 1200.0,
        "currency": "GEL",
        "rooms": 2,
        "area": 55.0,
        "district": "ვაკე",
        "url": f"https://www.myhome.ge/ru/{source_id}/",
        "photos": [f"https://static.example.com/{source_id}/1.jpg"],
        "phone": "+995555123456",
        "owner_name": "Нино",
    }
    values.update(overrides)
    return RawListing(**values)  # type: ignore[arg-type]


class FakeScraper(BaseScraper):
    """Отдаёт готовые карточки; запоминает, для каких открыл бы страницу объявления."""

    def __init__(self, listings: list[RawListing]) -> None:
        self.listings = listings
        self.fresh: list[str] = []

    async def scrape_listings(
        self, limit: int, needs_details: NeedsDetails | None = None
    ) -> list[RawListing]:
        cards = self.listings[:limit]
        self.fresh = [c.source_id for c in cards if needs_details is None or await needs_details(c)]
        return cards


async def count(session: AsyncSession, model: type[Listing] | type[District]) -> int:
    return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


async def test_create_and_update_from_raw(session: AsyncSession) -> None:
    repository = ListingsRepository(session)

    listing = await repository.create_or_update_from_raw(
        raw("1", language="ka", title="ბინა", description="ბინა ვაკეში")
    )
    # Заголовок — из данных на трёх языках; описание — как на сайте
    assert listing.title_ru == "2-комн. квартира, Ваке, 55 м²"
    assert listing.title_ka == "2-ოთახიანი ბინა, ვაკე, 55 მ²"
    assert (listing.description_ka, listing.description_ru) == ("ბინა ვაკეში", "")
    assert listing.images == ["https://static.example.com/1/1.jpg"]
    assert (listing.phone, listing.owner_name) == ("+995555123456", "Нино")
    assert listing.url == "https://www.myhome.ge/ru/1/"

    # Перевод на русский не затирается, если текст тот же (изменилась только цена).
    # Изменение текста сбрасывает перевод: test_translations_postgres.py
    listing.description_ru = "Квартира в Ваке (перевод)"
    updated = await repository.create_or_update_from_raw(
        raw("1", language="ka", title="ბინა", description="ბინა ვაკეში", price=1500.0)
    )
    assert updated.id == listing.id
    assert (updated.description_ka, updated.description_ru, updated.price) == (
        "ბინა ვაკეში",
        "Квартира в Ваке (перевод)",
        Decimal(1500),
    )


async def test_districts_are_reused_and_created(session: AsyncSession) -> None:
    session.add(
        District(
            name_ru="Ваке",
            name_ka="ვაკე",
            name_en="Vake",
            avg_price_per_m2=Decimal(20),
            safety_score=9,
        )
    )
    await session.flush()
    repository = ListingsRepository(session)

    await repository.create_or_update_from_raw(raw("1", district="Vake"))  # по name_en
    await repository.create_or_update_from_raw(raw("2", district="ვაკე"))  # по name_ka
    await repository.create_or_update_from_raw(raw("3", district="Didi Digomi"))  # новый

    names = (await session.execute(select(District.name_en).order_by(District.name_en))).scalars()
    assert list(names) == ["Didi Digomi", "Vake"]


async def test_pipeline_saves_commits_and_skips_unchanged(
    session_factory: async_sessionmaker[AsyncSession],
    session: AsyncSession,
) -> None:
    scraper = FakeScraper([raw("1"), raw("2", price=0), raw("3", district="Saburtalo")])

    first = await run_scrape(scraper, "myhome", 10, session_factory)
    second = await run_scrape(scraper, "myhome", 10, session_factory)

    assert (first.scraped, first.valid, first.changed, first.saved) == (3, 2, 2, 2)
    assert (second.changed, second.saved) == (0, 0), "цена не изменилась: дубликаты пропущены"
    assert await count(session, Listing) == 2

    # Сохранённое объявление сразу доступно в API с фото
    app = create_app(ApiSettings(), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/listings")).json()
    assert body["total"] == 2
    assert {item["images"][0] for item in body["items"]} == {
        "https://static.example.com/1/1.jpg",
        "https://static.example.com/3/1.jpg",
    }


@pytest.mark.parametrize("bad", [raw("1", rooms=0), raw("1", area=0)])
async def test_invalid_listings_are_not_saved(
    session_factory: async_sessionmaker[AsyncSession],
    session: AsyncSession,
    bad: RawListing,
) -> None:
    result = await run_scrape(FakeScraper([bad]), "myhome", 10, session_factory)

    assert result.saved == 0
    assert await count(session, Listing) == 0


async def test_detail_pages_only_for_new_and_changed(
    session_factory: async_sessionmaker[AsyncSession],
    session: AsyncSession,
) -> None:
    """Известное и не изменившееся объявление: страница не открывается, но отметка «видели» есть."""
    detailed = [raw(i, has_details=True) for i in ("1", "2", "3")]
    first = FakeScraper(detailed)
    await run_scrape(first, "myhome", 10, session_factory)
    assert first.fresh == ["1", "2", "3"]

    repository = ListingsRepository(session)
    gone = await repository.find_by_source("3", "myhome")
    assert gone is not None and gone.checked_at is not None
    seen_before = gone.checked_at
    gone.status = ListingStatus.ARCHIVED
    await session.commit()

    # Второй проход: карточки из списка; у «2» новая цена, «3» снова на сайте
    cards = [raw("1"), raw("2", price=1300.0), raw("3")]
    second = FakeScraper(cards)
    await run_scrape(second, "myhome", 10, session_factory)
    assert second.fresh == ["2", "3"]

    session.expire_all()
    unchanged = await repository.find_by_source("1", "myhome")
    back = await repository.find_by_source("3", "myhome")
    assert unchanged is not None and back is not None
    assert unchanged.details_fetched_at is not None, "данные страницы не затёрты списком"
    assert unchanged.checked_at is not None and unchanged.checked_at > seen_before
    assert back.status == ListingStatus.ACTIVE
