"""Калькулятор полной стоимости (TASK-103): ``GET /api/listings/{id}/costs``.

Аренда, залог, комиссия агента и примерные коммунальные по месяцам — в лари.
Доступно всем. Названия статей и пояснение — на языке пользователя.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from bina.application.costs import (
    GEL_RATES,
    ITEM_LABELS,
    NOTE,
    RANGE_PERCENT,
    CostEstimate,
    CostInput,
    CostItem,
    estimate_costs,
)
from bina.infrastructure.api.delivery import ui_language
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import bad_request, get_listing_or_404

router = APIRouter(prefix="/api/listings", tags=["listings"])


class CostItemOut(BaseModel):
    code: str
    title: str


class FirstMonthOut(BaseModel):
    rent: int
    deposit: int
    agency_fee: int
    utilities: int
    total: int


class MonthOut(BaseModel):
    month: str = Field(description="Месяц, ``2026-11``")
    items: dict[str, int] = Field(description="Статья → лари; пусто, если коммунальные включены")
    utilities: int
    total: int


class CostsOut(BaseModel):
    """Полная стоимость аренды; все суммы — в лари, округлены."""

    currency: str = "GEL"
    rent: int
    rent_currency: str = Field(description="Валюта объявления")
    exchange_rate: float = Field(description="Курс валюты объявления к лари")
    deposit: int
    agency_fee: int
    agent_listing: bool = Field(description="Объявление от агента: возможна комиссия")
    heating: str = Field(description="gas / electric — как считалось отопление")
    air_conditioning: bool
    people: int
    utilities_included: bool
    first_month: FirstMonthOut
    average_utilities: int
    average_month: int
    period_months: int
    period_total: int = Field(description="Аренда и коммунальные за срок + комиссия (без залога)")
    items: list[CostItemOut]
    monthly: list[MonthOut]
    range_percent: int
    note: str

    @classmethod
    def build(
        cls,
        estimate: CostEstimate,
        *,
        people: int,
        utilities_included: bool,
        agent_listing: bool,
        language: str,
    ) -> "CostsOut":
        first = estimate.months[0]
        return cls(
            rent=int(estimate.rent),
            rent_currency=estimate.rent_currency,
            exchange_rate=float(estimate.exchange_rate),
            deposit=int(estimate.deposit),
            agency_fee=int(estimate.agency_fee),
            agent_listing=agent_listing,
            heating=estimate.heating.value,
            air_conditioning=estimate.air_conditioning,
            people=people,
            utilities_included=utilities_included,
            first_month=FirstMonthOut(
                rent=int(estimate.rent),
                deposit=int(estimate.deposit),
                agency_fee=int(estimate.agency_fee),
                utilities=int(first.utilities),
                total=int(estimate.first_month_total),
            ),
            average_utilities=int(estimate.average_utilities),
            average_month=int(estimate.average_month),
            period_months=len(estimate.months),
            period_total=int(estimate.period_total),
            items=[
                CostItemOut(code=item.value, title=ITEM_LABELS[item][language]) for item in CostItem
            ],
            monthly=[
                MonthOut(
                    month=f"{month.month:%Y-%m}",
                    items={item.value: int(amount) for item, amount in month.items.items()},
                    utilities=int(month.utilities),
                    total=int(month.total),
                )
                for month in estimate.months
            ],
            range_percent=RANGE_PERCENT,
            note=NOTE[language].format(range=RANGE_PERCENT),
        )


def _start_month(value: str | None) -> date:
    if not value:
        today = datetime.now(UTC).date()
        return date(today.year, today.month, 1)
    try:
        year, month = (int(part) for part in value.split("-"))
        return date(year, month, 1)
    except ValueError as exc:
        raise bad_request("start must be YYYY-MM") from exc


@router.get("/{listing_id}/costs", response_model=CostsOut)
async def listing_costs(
    listing_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    people: Annotated[int, Query(ge=1, le=8)] = 2,
    months: Annotated[int, Query(ge=1, le=24)] = 12,
    start: Annotated[str | None, Query(description="Месяц въезда, YYYY-MM")] = None,
    deposit_months: Annotated[Decimal, Query(ge=0, le=3)] = Decimal(1),
    agency_fee_percent: Annotated[Decimal, Query(ge=0, le=100)] = Decimal(0),
    utilities_included: bool = False,
) -> CostsOut:
    """Первый месяц, средний месяц и сумма за срок; коммунальные по месяцам."""
    listing = await get_listing_or_404(session, listing_id)
    if listing.currency.upper() not in GEL_RATES:
        raise bad_request(f"unsupported currency: {listing.currency}")
    estimate = estimate_costs(
        CostInput(
            rent=listing.price,
            currency=listing.currency,
            area=float(listing.area),
            features=tuple(listing.features or ()),
            start=_start_month(start),
            months=months,
            people=people,
            deposit_months=deposit_months,
            agency_fee_percent=agency_fee_percent,
            utilities_included=utilities_included,
        )
    )
    return CostsOut.build(
        estimate,
        people=people,
        utilities_included=utilities_included,
        agent_listing=listing.owner_type == "agent",
        language=ui_language(user),
    )
