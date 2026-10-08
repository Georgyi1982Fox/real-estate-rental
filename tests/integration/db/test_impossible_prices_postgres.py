"""Ошибки хозяев в ценах уже сохранённых объявлений исправляются, на PostgreSQL."""

from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import ListingStatus
from bina.infrastructure.db.repositories.listings import ListingsRepository


def raw(source_id: str, price: float, area: float = 70.0, period: str = "monthly") -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="myhome",
        title=f"Квартира {source_id}",
        description="Описание",
        price=price,
        currency="GEL",
        rooms=2,
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
    await session.commit()

    assert await repository.fix_impossible_prices() == (1, 1)
    await session.commit()

    for listing in (normal, sale, daily, monthly_as_daily):
        await session.refresh(listing)
    assert normal.status == ListingStatus.ACTIVE
    assert sale.status == ListingStatus.ARCHIVED
    assert (daily.rent_period, monthly_as_daily.rent_period) == ("daily", "monthly")
    assert await repository.fix_impossible_prices() == (0, 0)
