"""Репозитории, которые использует бот, на настоящем PostgreSQL."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.infrastructure.db.models import District, Listing, ListingStatus
from bina.infrastructure.db.models.users import SubscriptionTier, UserRole
from bina.infrastructure.db.repositories import (
    DistrictsRepository,
    FavoritesRepository,
    ListingsRepository,
    UsersRepository,
)

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


async def add_district(session: AsyncSession, name: str) -> District:
    district = District(
        name_ru=name, name_ka=name, name_en=name, avg_price_per_m2=Decimal(10), safety_score=5
    )
    session.add(district)
    await session.flush()
    return district


async def add_listing(
    session: AsyncSession,
    district: District,
    n: int,
    price: int = 1000,
    rooms: int = 2,
    **kwargs: object,
) -> Listing:
    listing = Listing(
        source_id=f"src-{n}",
        source_name="test",
        title_ru=f"Объявление {n}",
        title_ka="ბინა",
        description_ru="",
        description_ka="",
        price=Decimal(price),
        district_id=district.id,
        rooms=rooms,
        area=Decimal(50),
        created_at=BASE_TIME + timedelta(minutes=n),
        **kwargs,
    )
    session.add(listing)
    await session.flush()
    return listing


async def test_user_create_persists_enum_values(session: AsyncSession) -> None:
    user = await UsersRepository(session).create(100, "en")
    await session.commit()

    row = (
        await session.execute(text("SELECT role::text, subscription_tier::text FROM bina_users"))
    ).one()
    assert tuple(row) == ("user", "free")
    assert user.role is UserRole.USER
    assert user.subscription_tier is SubscriptionTier.FREE


async def test_user_create_is_idempotent_and_restores_deleted(session: AsyncSession) -> None:
    repo = UsersRepository(session)
    first = await repo.create(100, "en")
    await session.execute(text("UPDATE bina_users SET is_deleted = true"))
    assert await repo.get_by_telegram_id(100) is None

    second = await repo.create(100, "ru")

    assert second.id == first.id
    assert second.is_deleted is False
    assert second.language == "en", "существующий пользователь сохраняет свой язык"
    assert (await repo.get_by_telegram_id(100)) is not None


async def test_update_language(session: AsyncSession) -> None:
    repo = UsersRepository(session)
    user = await repo.create(100, "ru")

    await repo.update_language(user.id, "ka")

    language = (await session.execute(text("SELECT language FROM bina_users"))).scalar()
    assert language == "ka"


async def test_listing_search_filters_and_order(session: AsyncSession) -> None:
    vake = await add_district(session, "Ваке")
    other = await add_district(session, "Сабуртало")
    await add_listing(session, vake, 1, price=900)
    in_range_old = await add_listing(session, vake, 2, price=1000)
    in_range_new = await add_listing(session, vake, 3, price=1500)
    await add_listing(session, vake, 4, price=1200, rooms=4)
    await add_listing(session, vake, 5, price=1200, status=ListingStatus.ARCHIVED)
    await add_listing(session, vake, 6, price=1200, is_deleted=True)
    await add_listing(session, other, 7, price=1200)
    repo = ListingsRepository(session)
    filters = ListingSearchFilters(
        district_id=vake.id,
        price_min=Decimal(1000),
        price_max=Decimal(1500),
        rooms_max=3,
    )

    assert await repo.count(filters) == 2
    assert [item.id for item in await repo.search(filters, limit=10)] == [
        in_range_new.id,
        in_range_old.id,
    ]
    assert [item.id for item in await repo.search(filters, limit=1, offset=1)] == [
        in_range_old.id
    ]
    assert await repo.count(ListingSearchFilters()) == 5


async def test_favorites(session: AsyncSession) -> None:
    user = await UsersRepository(session).create(100, "ru")
    district = await add_district(session, "Ваке")
    first = await add_listing(session, district, 1)
    second = await add_listing(session, district, 2)
    deleted = await add_listing(session, district, 3, is_deleted=True)
    repo = FavoritesRepository(session)

    await repo.add(user.id, first.id)
    await repo.add(user.id, first.id)  # идемпотентно
    await repo.add(user.id, deleted.id)
    await repo.add(user.id, second.id)

    assert await repo.exists(user.id, first.id)
    assert await repo.count_by_user(user.id) == 2
    listed = await repo.list_by_user(user.id, limit=10)
    assert {item.id for item in listed} == {first.id, second.id}
    assert await repo.filter_favorite_ids(user.id, [first.id, deleted.id]) == {
        first.id,
        deleted.id,
    }
    assert await repo.filter_favorite_ids(user.id, []) == set()

    assert await repo.remove(user.id, first.id) is True
    assert await repo.remove(user.id, first.id) is False
    assert not await repo.exists(user.id, first.id)


async def test_districts(session: AsyncSession) -> None:
    await add_district(session, "Сабуртало")
    vake = await add_district(session, "Ваке")
    repo = DistrictsRepository(session)

    assert [d.name_ru for d in await repo.list_all()] == ["Ваке", "Сабуртало"]
    found = await repo.get_by_id(vake.id)
    assert found is not None and found.name_ru == "Ваке"
