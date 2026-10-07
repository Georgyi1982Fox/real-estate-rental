"""Районы вида «Сабуртало/Картозия» склеиваются с «Сабуртало» на настоящем PostgreSQL."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import District, SavedSearch
from bina.infrastructure.db.repositories.districts import DistrictsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.users import UsersRepository


def raw(source_id: str, district: str) -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="korter",
        title=f"Квартира {source_id}",
        description="Описание",
        price=1000,
        currency="GEL",
        rooms=2,
        area=50.0,
        district=district,
        url=f"https://korter.example/{source_id}",
    )


async def test_new_listing_goes_to_district_without_street(session: AsyncSession) -> None:
    repository = ListingsRepository(session)
    plain = await repository.create_or_update_from_raw(raw("a", "Сабуртало"))
    street = await repository.create_or_update_from_raw(raw("b", "Сабуртало/Картозия"))
    unknown = await repository.create_or_update_from_raw(raw("c", "Гоциридзе/Зестафони"))

    assert street.district_id == plain.district_id
    district = await session.get(District, unknown.district_id)
    assert district is not None
    assert district.name_ru == "Гоциридзе"


async def test_merge_streets_moves_listings_and_searches(session: AsyncSession) -> None:
    districts = DistrictsRepository(session)
    real = await districts.create_district("Чугурети")
    # Старый «район с улицей», созданный до исправления
    junk = District(
        city="tbilisi",
        name_ka="ჩუგურეტი/ოტარ კაპანადზე",
        name_ru="Чугурети/Отар Капанадзе",
        name_en="Chugureti/Otar Kapanadze",
        avg_price_per_m2=0,
        safety_score=0,
    )
    orphan = District(
        city="tbilisi",
        name_ka="ვაკე/არაკიშვილი",
        name_ru="Ваке/Аракишвили",
        name_en="Vake/Arakishvili",
        avg_price_per_m2=0,
        safety_score=0,
    )
    session.add_all([junk, orphan])
    await session.flush()
    listings = ListingsRepository(session)
    listing = await listings.create_or_update_from_raw(raw("d", "Чугурети"))
    listing.district_id = junk.id
    user = await UsersRepository(session).create(901, "ru")
    one = SavedSearch(user_id=user.id, name="one", district_id=junk.id)
    many = SavedSearch(user_id=user.id, name="many", district_ids=[orphan.id, junk.id])
    session.add_all([one, many])
    await session.flush()

    assert await districts.merge_streets() == 2

    await session.refresh(listing)
    await session.refresh(one)
    await session.refresh(many)
    await session.refresh(junk)
    assert listing.district_id == real.id
    assert one.district_id == real.id
    assert junk.is_deleted
    vake = await districts.find("Ваке")
    assert vake is not None and vake.name_ru == "Ваке"
    assert many.district_ids == [vake.id, real.id]
    # Второй раз склеивать нечего
    assert await districts.merge_streets() == 0
    names = {d.name_ru for d in await districts.list_all("tbilisi")}
    assert not any("/" in name for name in names)
    assert (
        (await session.execute(select(District).where(District.id == orphan.id)))
        .scalar_one()
        .is_deleted
    )
