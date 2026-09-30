"""Тарифы, лимиты и продление подписки (TASK-026).

Избранное без ограничений на всех тарифах; бесплатный тариф ограничивает
сохранённые поиски, Premium даёт их больше.
Подписка оплачивается звёздами Telegram (XTR) и продлевается от даты окончания
текущей, если она ещё действует.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from bina.application.referrals import discounted_price
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import SubscriptionTier

# Payload счёта Telegram: "sub:<id тарифа>"
INVOICE_PREFIX = "sub:"
STARS_CURRENCY = "XTR"


@dataclass(frozen=True, slots=True)
class Plan:
    """Платный тариф."""

    id: str
    tier: SubscriptionTier
    days: int
    price_stars: int

    @property
    def invoice_payload(self) -> str:
        """Payload счёта: по нему бот узнаёт тариф при оплате."""
        return f"{INVOICE_PREFIX}{self.id}"


@dataclass(frozen=True, slots=True)
class Limits:
    """Ограничения тарифа; ``None`` — без ограничения."""

    favorites: int | None
    searches: int


FREE_LIMITS = Limits(favorites=None, searches=1)
PREMIUM_LIMITS = Limits(favorites=None, searches=20)


def is_premium(user: User, now: datetime) -> bool:
    """Платная подписка действует на момент ``now``."""
    expires = user.subscription_expires_at
    return user.subscription_tier != SubscriptionTier.FREE and expires is not None and expires > now


def effective_tier(user: User, now: datetime) -> SubscriptionTier:
    """Тариф с учётом срока: истёкшая подписка — бесплатный тариф."""
    return user.subscription_tier if is_premium(user, now) else SubscriptionTier.FREE


def limits_for(user: User, now: datetime) -> Limits:
    """Ограничения пользователя сейчас."""
    return PREMIUM_LIMITS if is_premium(user, now) else FREE_LIMITS


def plan_for_payload(plans: dict[str, Plan], payload: str) -> Plan | None:
    """Тариф по payload счёта (``None`` — чужой или устаревший счёт)."""
    if not payload.startswith(INVOICE_PREFIX):
        return None
    return plans.get(payload.removeprefix(INVOICE_PREFIX))


def price_for(plan: Plan, discounted: bool) -> int:
    """Цена в звёздах; ``discounted`` — скидка приглашённому другу (TASK-108)."""
    return discounted_price(plan.price_stars) if discounted else plan.price_stars


def validate_checkout(
    plans: dict[str, Plan],
    payload: str,
    currency: str,
    total_amount: int,
    discounted: bool = False,
) -> Plan | None:
    """Проверка перед оплатой: тариф существует, валюта и сумма совпадают.

    ``discounted``: пользователю положена скидка — принимается и цена со скидкой.
    Полная цена принимается всегда.
    """
    plan = plan_for_payload(plans, payload)
    if plan is None or currency != STARS_CURRENCY:
        return None
    allowed = {plan.price_stars, price_for(plan, discounted)}
    return plan if total_amount in allowed else None


def extended_until(user: User, plan: Plan, now: datetime) -> datetime:
    """Новая дата окончания: от текущей, если подписка действует, иначе от ``now``."""
    start = user.subscription_expires_at if is_premium(user, now) else now
    assert start is not None
    return start + timedelta(days=plan.days)
