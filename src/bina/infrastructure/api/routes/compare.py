"""Сравнение квартир (TASK-105): ``GET /api/listings/compare?ids=a,b,c``.

2-3 объявления в одной таблице: цены в лари, цена за м², въезд и средний месяц
(калькулятор TASK-103 с настройками по умолчанию), район и время до центра,
оценка цены и риска. ``best`` — у каких квартир лучшее значение в строке.
Доступно всем.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from bina.application.compare import MAX_ITEMS, MIN_ITEMS, ROWS, ComparedValues, best_in_rows
from bina.application.costs import GEL_RATES, CostInput, estimate_costs
from bina.application.district_guide import guide_for, minutes_to_center
from bina.application.fraud import fraud_level
from bina.application.use_cases.analyze_price import AnalyzePriceUseCase
from bina.infrastructure.api.delivery import ui_language
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import bad_request, get_listing_or_404
from bina.infrastructure.api.schemas import ListingOut
from bina.infrastructure.db.repositories.listings import ListingsRepository

router = APIRouter(prefix="/api/listings", tags=["listings"])

NOTE = {
    "ka": "ფასები ლარშია. შესვლისას და თვეში — მიახლოებით: 1 თვის დეპოზიტი, 2 ადამიანი.",
    "ru": "Цены в лари. Въезд и месяц — примерно: залог за 1 месяц, 2 человека.",
    "en": "Prices in GEL. Move-in and monthly costs are estimates: 1-month deposit, 2 people.",
}


class RowOut(BaseModel):
    code: str
    title: str


class ComparedOut(BaseModel):
    listing: ListingOut
    price: int = Field(description="Аренда в лари")
    price_per_m2: float | None = None
    area: float
    rooms: int
    floor: int | None = None
    total_floors: int | None = None
    district: str | None = None
    minutes_to_center: int | None = None
    metro: bool | None = None
    move_in: int
    average_month: int
    price_level: str = Field(description="below / fair / above / unknown")
    risk_level: str = Field(description="none / warning / high")
    features: list[str]


class CompareOut(BaseModel):
    currency: str = "GEL"
    rows: list[RowOut]
    items: list[ComparedOut]
    best: dict[str, list[UUID]] = Field(description="Строка → квартиры с лучшим значением")
    note: str


def _ids(values: list[str]) -> list[str]:
    ids = list(dict.fromkeys(part.strip() for value in values for part in value.split(",")))
    ids = [value for value in ids if value]
    if not MIN_ITEMS <= len(ids) <= MAX_ITEMS:
        raise bad_request(f"compare {MIN_ITEMS}-{MAX_ITEMS} different listings")
    return ids


@router.get("/compare", response_model=CompareOut)
async def compare_listings(
    ids: Annotated[list[str], Query(description="2-3 ID объявлений: через запятую или повтором")],
    user: CurrentUserDep,
    session: SessionDep,
) -> CompareOut:
    """Таблица сравнения 2-3 квартир."""
    language = ui_language(user)
    today = datetime.now(UTC).date()
    analyze = AnalyzePriceUseCase(ListingsRepository(session))
    items: list[ComparedOut] = []
    values: list[ComparedValues] = []
    for listing_id in _ids(ids):
        listing = await get_listing_or_404(session, listing_id)
        rate = GEL_RATES.get(listing.currency.upper())
        if rate is None:
            raise bad_request(f"unsupported currency: {listing.currency}")
        await session.refresh(listing, attribute_names=["district"])
        district = listing.district
        guide = guide_for(district.name_en) if district else None
        minutes = minutes_to_center(guide.latitude, guide.longitude) if guide else None
        costs = estimate_costs(
            CostInput(
                rent=listing.price,
                currency=listing.currency,
                area=float(listing.area),
                features=tuple(listing.features or ()),
                start=date(today.year, today.month, 1),
            )
        )
        area = float(listing.area)
        per_m2 = (costs.rent / Decimal(str(area))).quantize(Decimal("0.1")) if area else None
        risk = fraud_level(listing.fraud_score or 0).value
        features = list(listing.features or [])
        items.append(
            ComparedOut(
                listing=ListingOut.from_model(listing),
                price=int(costs.rent),
                price_per_m2=float(per_m2) if per_m2 is not None else None,
                area=area,
                rooms=listing.rooms,
                floor=listing.floor,
                total_floors=listing.total_floors,
                district=(
                    {"ka": district.name_ka, "ru": district.name_ru, "en": district.name_en}[
                        language
                    ]
                    if district
                    else None
                ),
                minutes_to_center=minutes,
                metro=guide.metro if guide else None,
                move_in=int(costs.first_month_total),
                average_month=int(costs.average_month),
                price_level=(await analyze.execute(listing)).level.value,
                risk_level=risk,
                features=features,
            )
        )
        values.append(
            ComparedValues(
                listing_id=listing.id,
                price=costs.rent,
                price_per_m2=per_m2,
                area=area,
                minutes_to_center=minutes,
                move_in=costs.first_month_total,
                average_month=costs.average_month,
                features=len(features),
                risk_level=risk,
            )
        )
    return CompareOut(
        rows=[RowOut(code=code, title=labels[language]) for code, labels in ROWS.items()],
        items=items,
        best=best_in_rows(values),
        note=NOTE[language],
    )
