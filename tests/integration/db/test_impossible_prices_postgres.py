"""Ошибки хозяев в ценах уже сохранённых объявлений исправляются, на PostgreSQL."""

from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import ListingStatus
from bina.infrastructure.db.repositories.listings import ListingsRepository


def raw(
    source_id: str, price: float, area: float = 70.0, period: str = "monthly", rooms: int = 2
) -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="myhome",
        title=f"Квартира {source_id}",
        description="Описание",
        price=price,
        currency="GEL",
        rooms=rooms,
        area=area,
        district="Дигоми",
        url=f"https://myhome.example/{source_id}",
        rent_period=period,
    )


async def test_fix_impossible_prices(session: AsyncSession) -> None:
    repository = ListingsRepository(session)
    normal = await repository.create_or_update_from_raw(raw("a", 2000))
    sale = await repository.create_or_update_from_raw(raw("b", 325488))
    daily = await repository.create_or_update_from_raw(raw("c", 150, period="daily"))
    monthly_as_daily = await repository.create_or_update_from_raw(raw("d", 4860, period="daily"))
    no_price = await repository.create_or_update_from_raw(raw("e", 1))
    daily_as_monthly = await repository.create_or_update_from_raw(raw("f", 60))
    extra_zero = await repository.create_or_update_from_raw(raw("g", 3903, area=1400, rooms=4))
    await session.commit()

    assert await repository.fix_impossible_prices() == {
        "to_monthly": 1,
        "to_daily": 1,
        "archived": 2,
        "area": 1,
    }
    await session.commit()

    listings = (normal, sale, daily, monthly_as_daily, no_price, daily_as_monthly, extra_zero)
    for listing in listings:
        await session.refresh(listing)
    assert normal.status == ListingStatus.ACTIVE
    assert (sale.status, no_price.status) == (ListingStatus.ARCHIVED, ListingStatus.ARCHIVED)
    assert (daily.rent_period, monthly_as_daily.rent_period) == ("daily", "monthly")
    assert daily_as_monthly.rent_period == "daily"
    assert float(extra_zero.area) == 140.0
    assert await repository.fix_impossible_prices() == dict.fromkeys(
        ("to_monthly", "to_daily", "archived", "area"), 0
    )
