"""Режим тестирования: платные функции для всех (PREMIUM_FOR_ALL)."""

from datetime import UTC, datetime

import pytest

from bina.application.subscriptions import (
    FREE_LIMITS,
    PREMIUM_LIMITS,
    has_premium_access,
    is_premium,
    limits_for,
    premium_for_all,
)
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import SubscriptionTier

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def free_user() -> User:
    return User(subscription_tier=SubscriptionTier.FREE, subscription_expires_at=None)


@pytest.mark.parametrize("value", ["", "0", "no", "false"])
def test_off(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("PREMIUM_FOR_ALL", value)
    assert not premium_for_all()
    assert not has_premium_access(free_user(), NOW)
    assert limits_for(free_user(), NOW) == FREE_LIMITS


@pytest.mark.parametrize("value", ["1", "true", "YES"])
def test_on(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("PREMIUM_FOR_ALL", value)
    user = free_user()
    assert has_premium_access(user, NOW)
    assert limits_for(user, NOW) == PREMIUM_LIMITS
    # Статус подписки и оплата — по-настоящему: бесплатный тариф остаётся бесплатным
    assert not is_premium(user, NOW)
