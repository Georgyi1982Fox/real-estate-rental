"""«Весь город» вместо района с названием города (TASK-122), на PostgreSQL."""

import importlib.util
from datetime import UTC, datetime, timedelta
from types import ModuleType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import District, SavedSearch
from bina.infrastructure.db.repositories.districts import DistrictsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from tests.integration.conftest import VERSIONS


def raw(source_id: str, district: str, city: str = "batumi") -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="ss",
        title=f"Квартира {source_id}",
        description="Описание",
        price=1000,
        currency="GEL",
        rooms=2,
        area=50.0,
        district=district,
        city=city,
        url=f"https://ss.example/{source_id}",
    )


def migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("city_wide", VERSIONS / "city_wide_districts.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_listing_without_district_goes_to_whole_city(session: AsyncSession) -> None:
    """Сайт написал город или «Unknown» — объявление «весь город», не «район Батуми»."""
    listings = ListingsRepository(session)
    named = await listings.create_or_update_from_raw(raw("a", "Батуми"))
    ss_title = await listings.create_or_update_from_raw(raw("b", "Районы Батуми"))
    unknown = await listings.create_or_update_from_raw(raw("c", "Unknown"))
    real = await listings.create_or_update_from_raw(raw("d", "Старый Батуми"))
    tbilisi = await listings.create_or_update_from_raw(raw("e", "Тбилиси", "tbilisi"))
    await session.commit()

    assert named.district_id == ss_title.district_id == unknown.district_id
    whole = await session.get(District, named.district_id)
    assert whole is not None and whole.is_city_wide
    assert (whole.name_ka, whole.name_ru, whole.name_en) == ("ბათუმი", "Батуми", "Batumi")
    assert tbilisi.district_id != whole.id, "у каждого города свой «весь город»"

    districts = DistrictsRepository(session)
    assert [d.id for d in await districts.list_all("batumi")] == [real.district_id]
    with_names = await districts.list_all(with_city_wide=True)
    assert {d.id for d in with_names} >= {whole.id, real.district_id, tbilisi.district_id}


async def test_migration_merges_city_named_districts(session: AsyncSession) -> None:
    """Старые «районы» Батуми, Районы Батуми, Unknown склеиваются в один «весь город»."""

    start = datetime.now(UTC) - timedelta(days=30)
    created: list[District] = []

    def district(name_ru: str, name_en: str, name_ka: str, city: str = "batumi") -> District:
        # Порядок создания: «весь город» — самый старый из «районов-городов»
        item = District(
            created_at=start + timedelta(minutes=len(created)),
            city=city,
            name_ru=name_ru,
            name_en=name_en,
            name_ka=name_ka,
            avg_price_per_m2=0,
            safety_score=0,
        )
        created.append(item)
        return item

    first = district("Батуми", "Batumi", "ბატუმი")
    second = district("Районы Батуми", "Rayony Batumi", "რაიონი ბატუმი")
    unknown = district("Unknown", "Unknown", "უნკნოვნ")
    real = district("Старый Батуми", "Old Batumi", "ძველი ბათუმი")
    gonio = district("Гонио", "Gonio", "გონიო")
    session.add_all([first, second, unknown, real, gonio])
    await session.flush()
    listings = ListingsRepository(session)
    listing = await listings.create_or_update_from_raw(raw("m", "Старый Батуми"))
    listing.district_id = second.id
    user = await UsersRepository(session).create(902, "ru")
    one = SavedSearch(user_id=user.id, name="one", district_id=unknown.id)
    many = SavedSearch(user_id=user.id, name="many", district_ids=[real.id, second.id])
    session.add_all([one, many])
    ids = {
        name: item.id
        for name, item in (
            ("first", first),
            ("second", second),
            ("unknown", unknown),
            ("real", real),
            ("gonio", gonio),
            ("listing", listing),
        )
    }
    await session.commit()

    module = migration()
    await session.run_sync(lambda sync: module.merge_city_wide(sync.connection()))
    await session.commit()
    session.expire_all()

    kept = await session.get(District, ids["first"])
    assert kept is not None and kept.is_city_wide and not kept.is_deleted
    assert (kept.name_ka, kept.name_ru, kept.name_en) == ("ბათუმი", "Батуми", "Batumi")
    for copy in ("second", "unknown"):
        merged = await session.get(District, ids[copy])
        assert merged is not None and merged.is_deleted
    for other in ("real", "gonio"):
        stays = await session.get(District, ids[other])
        assert stays is not None and not stays.is_city_wide and not stays.is_deleted
    moved = await listings.get_by_id(ids["listing"])
    assert moved is not None and moved.district_id == ids["first"]
    searches = {s.name: s for s in (await session.execute(select(SavedSearch))).scalars()}
    assert searches["one"].district_id == ids["first"]
    assert searches["many"].district_ids == [ids["real"], ids["first"]]
