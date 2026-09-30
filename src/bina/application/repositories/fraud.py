"""Порт хранилища для антифрода (TASK-011)."""

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from bina.application.rent_period import MONTHLY
from bina.infrastructure.db.models import Listing


class IFraudRepository(Protocol):
    """Объявления, которые ещё не проверены, и сохранение оценки."""

    async def list_fraud_unchecked(self, limit: int) -> list[Listing]:
        """Активные объявления без проверки (новые сверху), с загруженным районом."""
        ...

    async def district_median_per_m2(
        self, district_id: UUID, currency: str, rent_period: str = MONTHLY
    ) -> Decimal | None:
        """Медиана цены за м² активных объявлений района того же вида аренды; None — мало данных."""
        ...

    async def save_fraud(self, listing_id: UUID, score: int, reasons: list[str]) -> None:
        """Записать оценку и время проверки."""
        ...
