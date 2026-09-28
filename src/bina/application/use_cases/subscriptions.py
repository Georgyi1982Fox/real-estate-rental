"""Оплата подписки звёздами Telegram (TASK-026/027)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import structlog

from bina.application.repositories.payments import IPaymentsRepository
from bina.application.repositories.users import IUsersRepository
from bina.application.subscriptions import STARS_CURRENCY, Plan, extended_until
from bina.infrastructure.db.models import User

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ActivationResult:
    """Итог активации."""

    expires_at: datetime | None
    # False — этот платёж уже был учтён (Telegram доставил апдейт повторно)
    activated: bool


class ActivateSubscriptionUseCase:
    """Записывает успешный платёж и продлевает подписку. Идемпотентен по ID платежа."""

    def __init__(self, payments: IPaymentsRepository, users: IUsersRepository) -> None:
        self._payments = payments
        self._users = users

    async def execute(
        self, user: User, plan: Plan, charge_id: str, amount: int, now: datetime
    ) -> ActivationResult:
        """Не коммитит: транзакцией управляет вызывающий код."""
        if await self._payments.exists(charge_id):
            logger.info("Payment already processed", charge_id=charge_id)
            return ActivationResult(expires_at=user.subscription_expires_at, activated=False)

        expires_at = extended_until(user, plan, now)
        await self._payments.add_success(
            user_id=user.id,
            amount=Decimal(amount),
            currency=STARS_CURRENCY,
            provider_payment_id=charge_id,
            plan=plan.id,
        )
        await self._users.set_subscription(user.id, plan.tier, expires_at)
        user.subscription_tier = plan.tier
        user.subscription_expires_at = expires_at
        logger.info("Subscription activated", user_id=str(user.id), plan=plan.id, until=expires_at)
        return ActivationResult(expires_at=expires_at, activated=True)
