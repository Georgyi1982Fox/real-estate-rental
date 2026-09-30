"""Анализ цены объявления: дешевле или дороже обычного (TASK-093)."""

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from bina.application.price_analysis import (
    MIN_SAMPLES,
    UNKNOWN,
    PriceAnalysis,
    PriceBasis,
    compare_price,
)
from bina.application.rent_period import MONTHLY
from bina.infrastructure.db.models import Listing


class IPriceStatsRepository(Protocol):
    """Статистика цен."""

    async def rooms_median_price(
        self, district_id: UUID, rooms: int, currency: str, rent_period: str = MONTHLY
    ) -> tuple[int, Decimal | None]: ...

    async def district_price_per_m2(
        self, district_id: UUID, currency: str, rent_period: str = MONTHLY
    ) -> tuple[int, Decimal | None]: ...


class AnalyzePriceUseCase:
    """Сравнивает цену с похожими квартирами района."""

    def __init__(self, listings: IPriceStatsRepository) -> None:
        self._listings = listings

    async def execute(self, listing: Listing) -> PriceAnalysis:
        price = Decimal(str(listing.price))
        # Сравнение с тем же видом аренды: у посуточной цена за сутки (TASK-092)
        count, median = await self._listings.rooms_median_price(
            listing.district_id, listing.rooms, listing.currency, listing.rent_period
        )
        if median is not None and count >= MIN_SAMPLES:
            return compare_price(price, median, count, PriceBasis.DISTRICT_ROOMS)
        # Похожих по комнатам мало — по цене за м² района
        area = Decimal(str(listing.area or 0))
        if area <= 0:
            return UNKNOWN
        count, per_m2 = await self._listings.district_price_per_m2(
            listing.district_id, listing.currency, listing.rent_period
        )
        if per_m2 is not None and count >= MIN_SAMPLES:
            return compare_price(price, per_m2 * area, count, PriceBasis.DISTRICT_M2)
        return UNKNOWN
