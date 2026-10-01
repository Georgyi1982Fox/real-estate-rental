"""Заголовки объявлений собираются из данных на трёх языках, на PostgreSQL."""

import dataclasses
import importlib.util
from decimal import Decimal
from pathlib import Path
from typing import Any

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Connection, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bina.application.listing_titles import listing_titles
from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import District, Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository

MIGRATION = (
    Path(__file__).parents[3]
    / "src/bina/infrastructure/db/alembic/versions/listing_generated_titles.py"
)


def flat(source_id: str, **fields: Any) -> RawListing:
    base = RawListing(
        source_id=source_id,
        source_name="ss",
        title="Аренда 2-комнатная Квартира. Мтацминда",
        description="Квартира с ремонтом.",
        price=1500.0,
        currency="GEL",
        rooms=2,
        area=35.0,
        district="Мтацминда",
        url=f"https://ss.example/{source_id}",
    )
    return dataclasses.replace(base, **fields)


async def test_new_listing_titles_in_all_languages(session: AsyncSession) -> None:
    listing = await ListingsRepository(session).create_or_update_from_raw(flat("1"))
    await session.commit()

    assert listing.title_ru == "2-комн. квартира, Мтацминда, 35 м²"
    assert listing.title_ka.startswith("2-ოთახიანი ბინა, ")
    assert listing.title_ka.endswith(", 35 მ²")
    assert "Мтацминда" not in listing.title_ka, "район тоже по-грузински"
    assert listing.title_en.startswith("2-room apartment, ")
    assert listing.description_ru == "Квартира с ремонтом."
    assert listing.description_ka == "", "описание переведёт AI"


async def test_update_keeps_description_translations(session: AsyncSession) -> None:
    repository = ListingsRepository(session)
    listing = await repository.create_or_update_from_raw(flat("2"))
    listing.description_ka = "ბინა რემონტით."
    await session.commit()

    again = await repository.create_or_update_from_raw(flat("2", price=1400.0))
    await session.commit()

    assert again.description_ka == "ბინა რემონტით.", "описание не менялось — перевод цел"
    assert again.title_ru == "2-комн. квартира, Мтацминда, 35 м²"


async def test_migration_rebuilds_old_titles(engine: AsyncEngine, session: AsyncSession) -> None:
    """Старые объявления: заголовки сайта → те же заголовки, что у новых."""
    repository = ListingsRepository(session)
    monthly = await repository.create_or_update_from_raw(flat("3", area=72.5))
    daily = await repository.create_or_update_from_raw(
        flat("4", rooms=1, area=40.0, rent_period="daily")
    )
    await session.execute(
        update(Listing).values(title_ru="Аренда квартиры", title_ka="", title_en="")
    )
    await session.commit()

    spec = importlib.util.spec_from_file_location("listing_generated_titles", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def run(connection: Connection) -> None:
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()

    async with engine.begin() as connection:
        await connection.run_sync(run)

    for listing in (monthly, daily):
        await session.refresh(listing)
        district = await session.get(District, listing.district_id)
        assert district is not None
        expected = listing_titles(
            listing.rooms,
            Decimal(listing.area),
            listing.rent_period,
            {"ru": district.name_ru, "en": district.name_en, "ka": district.name_ka},
        )
        assert {
            "title_ru": listing.title_ru,
            "title_en": listing.title_en,
            "title_ka": listing.title_ka,
        } == expected
    assert daily.title_ru == "Посуточно: 1-комн. квартира, Мтацминда, 40 м²"
    assert monthly.title_en.endswith(", 72.5 m²")
