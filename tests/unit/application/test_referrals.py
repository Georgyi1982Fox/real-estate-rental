"""Правила приглашений (TASK-108)."""

from datetime import UTC, datetime

from bina.application.localization import script_of
from bina.application.referrals import (
    CODE_ALPHABET,
    CODE_LENGTH,
    REWARD_TEXTS,
    code_from_start,
    discounted_price,
    invite_link,
    month_start,
    new_code,
)
from bina.application.subscriptions import Plan, validate_checkout
from bina.infrastructure.db.models.users import SubscriptionTier


def test_codes() -> None:
    code = new_code()
    assert len(code) == CODE_LENGTH and set(code) <= set(CODE_ALPHABET)
    assert code_from_start(f"ref_{code}") == code
    assert code_from_start(f"ref_{code.upper()}") == code
    for bad in (None, "", code, "ref_short", "ref_il0oil0o", "search"):
        assert code_from_start(bad) is None
    assert invite_link("bina_bot", code) == f"https://t.me/bina_bot?start=ref_{code}"


def test_discount_and_checkout() -> None:
    assert (discounted_price(250), discounted_price(100), discounted_price(1)) == (200, 80, 1)
    plan = Plan(id="premium_month", tier=SubscriptionTier.NOMAD, days=30, price_stars=250)
    plans = {plan.id: plan}
    assert validate_checkout(plans, "sub:premium_month", "XTR", 200) is None
    assert validate_checkout(plans, "sub:premium_month", "XTR", 200, discounted=True) == plan
    assert validate_checkout(plans, "sub:premium_month", "XTR", 250, discounted=True) == plan


def test_month_start_and_texts() -> None:
    assert month_start(datetime(2026, 10, 17, 15, 30, tzinfo=UTC)) == datetime(
        2026, 10, 1, tzinfo=UTC
    )
    for language in ("ka", "ru", "en"):
        assert script_of(REWARD_TEXTS[language]) == language
