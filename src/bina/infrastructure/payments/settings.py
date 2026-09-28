"""Тарифы из переменных окружения (TASK-026)."""

import os
from collections.abc import Mapping

from bina.application.subscriptions import Plan
from bina.infrastructure.db.models.users import SubscriptionTier

PREMIUM_MONTH = "premium_month"


def load_plans(env: Mapping[str, str] | None = None) -> dict[str, Plan]:
    """Доступные тарифы. Цена — ``PREMIUM_PRICE_STARS`` (250), срок — ``PREMIUM_DAYS`` (30)."""
    source = os.environ if env is None else env
    price = int(source.get("PREMIUM_PRICE_STARS", "") or 250)
    days = int(source.get("PREMIUM_DAYS", "") or 30)
    if price < 1 or days < 1:
        raise ValueError("PREMIUM_PRICE_STARS and PREMIUM_DAYS must be positive")
    plan = Plan(id=PREMIUM_MONTH, tier=SubscriptionTier.NOMAD, days=days, price_stars=price)
    return {plan.id: plan}
