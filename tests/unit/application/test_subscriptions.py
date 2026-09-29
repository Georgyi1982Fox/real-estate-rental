"""Политика тарифов (TASK-026)."""

from datetime import UTC, datetime, timedelta

import pytest

from bina.application.subscriptions import (
    FREE_LIMITS,
    PREMIUM_LIMITS,
    effective_tier,
    extended_until,
    is_premium,
    limits_for,
    validate_checkout,
)
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.payments.settings import PREMIUM_MONTH, PREMIUM_WEEK, load_plans

NOW = datetime(2026, 9, 28, 12, tzinfo=UTC)
PLANS = load_plans({})
PLAN = PLANS[PREMIUM_MONTH]


def user(tier: SubscriptionTier = SubscriptionTier.FREE, expires: datetime | None = None) -> User:
    return User(subscription_tier=tier, subscription_expires_at=expires)


@pytest.mark.parametrize(
    ("tier", "expires", "premium"),
    [
        (SubscriptionTier.FREE, None, False),
        (SubscriptionTier.FREE, NOW + timedelta(days=5), False),
        (SubscriptionTier.NOMAD, None, False),
        (SubscriptionTier.NOMAD, NOW - timedelta(seconds=1), False),
        (SubscriptionTier.NOMAD, NOW + timedelta(days=1), True),
    ],
)
def test_is_premium(tier: SubscriptionTier, expires: datetime | None, premium: bool) -> None:
    u = user(tier, expires)
    assert is_premium(u, NOW) is premium
    assert limits_for(u, NOW) == (PREMIUM_LIMITS if premium else FREE_LIMITS)
    assert effective_tier(u, NOW) == (tier if premium else SubscriptionTier.FREE)


def test_extended_until() -> None:
    assert extended_until(user(), PLAN, NOW) == NOW + timedelta(days=30)
    expired = user(SubscriptionTier.NOMAD, NOW - timedelta(days=3))
    assert extended_until(expired, PLAN, NOW) == NOW + timedelta(days=30)
    active = user(SubscriptionTier.NOMAD, NOW + timedelta(days=3))
    assert extended_until(active, PLAN, NOW) == NOW + timedelta(days=33)


def test_validate_checkout() -> None:
    assert validate_checkout(PLANS, "sub:premium_month", "XTR", 250) == PLAN
    assert validate_checkout(PLANS, "sub:premium_month", "XTR", 249) is None
    assert validate_checkout(PLANS, "sub:premium_month", "USD", 250) is None
    assert validate_checkout(PLANS, "premium_month", "XTR", 250) is None
    assert validate_checkout(PLANS, "sub:family", "XTR", 250) is None


def test_load_plans_from_env() -> None:
    plan = load_plans({"PREMIUM_PRICE_STARS": "300", "PREMIUM_DAYS": "31"})[PREMIUM_MONTH]
    assert (plan.price_stars, plan.days, plan.tier) == (300, 31, SubscriptionTier.NOMAD)
    with pytest.raises(ValueError):
        load_plans({"PREMIUM_PRICE_STARS": "0"})


def test_week_plan() -> None:
    """TASK-084: пропуск на неделю рядом с месяцем; месяц остаётся первым (основным)."""
    plans = load_plans({})
    assert list(plans) == [PREMIUM_MONTH, PREMIUM_WEEK]
    week = plans[PREMIUM_WEEK]
    assert (week.price_stars, week.days, week.tier) == (100, 7, SubscriptionTier.NOMAD)
    assert validate_checkout(plans, "sub:premium_week", "XTR", 100) == week
    assert validate_checkout(plans, "sub:premium_week", "XTR", 250) is None

    custom = load_plans({"PREMIUM_WEEK_PRICE_STARS": "80", "PREMIUM_WEEK_DAYS": "10"})
    assert (custom[PREMIUM_WEEK].price_stars, custom[PREMIUM_WEEK].days) == (80, 10)
    assert list(load_plans({"PREMIUM_WEEK_PRICE_STARS": "0"})) == [PREMIUM_MONTH]
    with pytest.raises(ValueError):
        load_plans({"PREMIUM_WEEK_DAYS": "0"})
