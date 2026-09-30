"""Тбилиси и Батуми в одной базе (TASK-079), на PostgreSQL."""

import dataclasses
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.repositories.districts import DistrictsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository


def flat(source_id: str, **fields: Any) -> RawListing:
    base = RawListing(
        source_id=source_id,
        source_name="ss",
        title=f"Квартира {source_id}",
        description="Описание",
        price=1000.0,
        currency="GEL",
        rooms=2,
        area=60.0,
        district="Центр",
        url=f"https://ss.example/{source_id}",
    )
    return dataclasses.replace(base, **fields)


async def test_same_district_name_in_two_cities(session: AsyncSession) -> None:
    listings = ListingsRepository(session)
    tbilisi = await listings.create_or_update_from_raw(flat("T1"))
    batumi = await listings.create_or_update_from_raw(flat("B1", city="batumi"))
    again = await listings.create_or_update_from_raw(flat("B2", city="batumi"))
    await session.commit()

    assert tbilisi.district_id != batumi.district_id, "«Центр» Батуми — не район Тбилиси"
    assert batumi.district_id == again.district_id

    districts = DistrictsRepository(session)
    assert await districts.cities() == ["tbilisi", "batumi"]
    assert [d.city for d in await districts.list_all("batumi")] == ["batumi"]
    assert len(await districts.list_all()) == 2

    found = await listings.search(ListingSearchFilters(city="batumi"), limit=10)
    assert sorted(item.source_id for item in found) == ["B1", "B2"]
    assert await listings.count(ListingSearchFilters(city="tbilisi")) == 1
    assert await listings.count(ListingSearchFilters()) == 3


async def test_batumi_district_names_from_dictionary(session: AsyncSession) -> None:
    listing = await ListingsRepository(session).create_or_update_from_raw(
        flat("B3", city="batumi", district="Старий Батуми")
    )
    await session.commit()
    district = await DistrictsRepository(session).get_by_id(listing.district_id)
    assert district is not None
    assert (district.name_ru, district.name_en, district.name_ka, district.city) == (
        "Старый Батуми",
        "Old Batumi",
        "ძველი ბათუმი",
        "batumi",
    )
