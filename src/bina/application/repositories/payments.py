"""Порт хранилища платежей (TASK-026)."""

from decimal import Decimal
from typing import Protocol
from uuid import UUID


class IPaymentsRepository(Protocol):
    """Платежи пользователей."""

    async def exists(self, provider_payment_id: str) -> bool:
        """Платёж с таким ID провайдера уже записан (повторная доставка апдейта)."""
        ...

    async def add_success(
        self,
        user_id: UUID,
        amount: Decimal,
        currency: str,
        provider_payment_id: str,
        plan: str,
    ) -> None:
        """Записать успешный платёж звёздами Telegram."""
        ...
