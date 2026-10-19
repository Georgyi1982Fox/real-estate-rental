"""«🔥 Топ» для гостиницы (TASK-120, этап 2). Не коммитит."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import structlog

from bina.application.hotel_promotion import (
    HOTEL_PROMOTION_PLAN,
    hotel_from_payload,
    hotel_promotion_price,
)
from bina.application.hotels import NOT_ACTIVE, NOT_FOUND, HotelError
from bina.application.promotion import extended_promotion
from bina.application.subscriptions import STARS_CURRENCY
from bina.infrastructure.db.models import Hotel
from bina.infrastructure.db.repositories.payments import PaymentsRepository

logger = structlog.get_logger(__name__)


class IHotelPromotionRepository(Protocol):
    async def owned(self, owner_id: UUID, hotel_id: UUID) -> Hotel | None: ...

    async def set_promotion(self, hotel: Hotel, until: datetime) -> None: ...


@dataclass(frozen=True, slots=True)
class HotelPromotionResult:
    hotel: Hotel
    until: datetime
    # False — платёж уже учтён (Telegram прислал его повторно)
    activated: bool


def is_listed(hotel: Hotel) -> bool:
    """Объект виден в разделе: включён, не скрыт, есть номер с ценой."""
    return hotel.is_active and hotel.hidden_at is None and hotel.min_price_gel is not None


class HotelPromotionUseCase:
    def __init__(self, hotels: IHotelPromotionRepository, payments: PaymentsRepository) -> None:
        self._hotels = hotels
        self._payments = payments

    async def promotable(self, owner_id: UUID, hotel_id: UUID) -> Hotel:
        """Свой объект, который виден в разделе; иначе :class:`HotelError`."""
        hotel = await self._hotels.owned(owner_id, hotel_id)
        if hotel is None:
            raise HotelError(NOT_FOUND)
        if not is_listed(hotel):
            raise HotelError(NOT_ACTIVE)
        return hotel

    async def check_payment(self, owner_id: UUID, payload: str, currency: str, amount: int) -> bool:
        """Перед списанием: объект свой и виден, сумма и валюта верны."""
        hotel_id = hotel_from_payload(payload)
        if hotel_id is None or currency != STARS_CURRENCY or amount != hotel_promotion_price():
            return False
        try:
            await self.promotable(owner_id, hotel_id)
        except HotelError:
            return False
        return True

    async def activate(
        self, owner_id: UUID, payload: str, charge_id: str, amount: int, now: datetime
    ) -> HotelPromotionResult | None:
        """Звёзды списаны: записать платёж и поднять в «Топ». ``None`` — объекта нет."""
        hotel_id = hotel_from_payload(payload)
        hotel = await self._hotels.owned(owner_id, hotel_id) if hotel_id is not None else None
        if hotel is None:
            return None
        if await self._payments.exists(charge_id):
            logger.info("Hotel promotion payment already processed", charge_id=charge_id)
            return HotelPromotionResult(hotel, hotel.promoted_until or now, activated=False)
        until = extended_promotion(hotel.promoted_until, now)
        await self._payments.add_success(
            user_id=owner_id,
            amount=Decimal(amount),
            currency=STARS_CURRENCY,
            provider_payment_id=charge_id,
            plan=HOTEL_PROMOTION_PLAN,
        )
        await self._hotels.set_promotion(hotel, until)
        logger.info("Hotel promoted", hotel_id=str(hotel.id), until=until)
        return HotelPromotionResult(hotel, until, activated=True)
