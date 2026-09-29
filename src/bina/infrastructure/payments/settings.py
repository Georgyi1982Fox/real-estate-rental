"""Тарифы из переменных окружения (TASK-026, TASK-084)."""

import os
from collections.abc import Mapping

from bina.application.subscriptions import Plan
from bina.infrastructure.db.models.users import SubscriptionTier

PREMIUM_MONTH = "premium_month"
# Пропуск на время поиска квартиры: обычно ищут 2-4 недели (TASK-084)
PREMIUM_WEEK = "premium_week"


def _positive(source: Mapping[str, str], name: str, default: int) -> int:
    value = int(source.get(name, "") or default)
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def load_plans(env: Mapping[str, str] | None = None) -> dict[str, Plan]:
    """Доступные тарифы (первый — основной).

    Месяц: ``PREMIUM_PRICE_STARS`` (250) за ``PREMIUM_DAYS`` (30).
    Неделя: ``PREMIUM_WEEK_PRICE_STARS`` (100) за ``PREMIUM_WEEK_DAYS`` (7);
    ``PREMIUM_WEEK_PRICE_STARS=0`` убирает недельный тариф.
    """
    source = os.environ if env is None else env
    month = Plan(
        id=PREMIUM_MONTH,
        tier=SubscriptionTier.NOMAD,
        days=_positive(source, "PREMIUM_DAYS", 30),
        price_stars=_positive(source, "PREMIUM_PRICE_STARS", 250),
    )
    plans = {month.id: month}
    if source.get("PREMIUM_WEEK_PRICE_STARS", "").strip() != "0":
        week = Plan(
            id=PREMIUM_WEEK,
            tier=SubscriptionTier.NOMAD,
            days=_positive(source, "PREMIUM_WEEK_DAYS", 7),
            price_stars=_positive(source, "PREMIUM_WEEK_PRICE_STARS", 100),
        )
        plans[week.id] = week
    return plans
