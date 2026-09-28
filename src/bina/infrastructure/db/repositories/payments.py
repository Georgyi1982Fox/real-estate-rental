"""Платежи в PostgreSQL (TASK-026)."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.repositories.payments import IPaymentsRepository
from bina.infrastructure.db.models import Payment
from bina.infrastructure.db.models.payments import PaymentProvider, PaymentStatus


class PaymentsRepository(IPaymentsRepository):
    """Платежи пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, provider_payment_id: str) -> bool:
        """Платёж с таким ID провайдера уже записан."""
        query = select(Payment.id).where(Payment.provider_payment_id == provider_payment_id)
        return (await self._session.execute(query)).first() is not None

    async def add_success(
        self,
        user_id: UUID,
        amount: Decimal,
        currency: str,
        provider_payment_id: str,
        plan: str,
    ) -> None:
        """Записать успешный платёж звёздами Telegram."""
        self._session.add(
            Payment(
                user_id=user_id,
                amount=amount,
                currency=currency,
                provider=PaymentProvider.TELEGRAM_STARS,
                provider_payment_id=provider_payment_id,
                status=PaymentStatus.SUCCESS,
                plan=plan,
            )
        )
        await self._session.flush()
