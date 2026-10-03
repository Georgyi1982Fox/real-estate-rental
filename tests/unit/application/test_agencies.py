"""Пакеты агентств, лимиты и ежедневное поднятие (TASK-100)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from bina.application.agencies import (
    AgencyPlan,
    bump_due,
    bump_hour,
    listing_from_bump_payload,
    listing_limit,
    load_agency_plans,
    plan_for_payload,
)

NOW = datetime(2026, 10, 3, 20, 0, tzinfo=UTC)  # 00:00 в Тбилиси (+4)


def test_default_plans_sorted_by_size() -> None:
    plans = load_agency_plans({})
    assert [(p.id, p.listings, p.price_stars) for p in plans.values()] == [
        ("start", 20, 300),
        ("pro", 30, 450),
        ("business", 40, 600),
    ]
    assert plan_for_payload(plans, "agency:pro") == plans["pro"]
    assert plan_for_payload(plans, "agency:nope") is None


@pytest.mark.parametrize("raw", ["broken", "a:0:10", "a:10"])
def test_bad_plans_fall_back_to_defaults(raw: str) -> None:
    assert list(load_agency_plans({"AGENCY_PLANS": raw})) == ["start", "pro", "business"]


def test_custom_plans() -> None:
    plans = load_agency_plans({"AGENCY_PLANS": "big:100:1500, small:15:200"})
    assert list(plans) == ["small", "big"]


def test_listing_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PREMIUM_FOR_ALL", raising=False)
    monkeypatch.delenv("AGENCY_FREE_LISTINGS", raising=False)
    plans = {"start": AgencyPlan("start", 20, 300), "big": AgencyPlan("big", 40, 600)}
    assert listing_limit(plans, None, None, NOW) == 10
    assert listing_limit(plans, "start", NOW + timedelta(days=1), NOW) == 20
    assert listing_limit(plans, "start", NOW - timedelta(days=1), NOW) == 10, "закончился"
    monkeypatch.setenv("PREMIUM_FOR_ALL", "1")
    assert listing_limit(plans, None, None, NOW) == 40, "тестовый режим — самый большой"


def test_bump_hours_spread_over_the_day() -> None:
    hours = {bump_hour(uuid4()) for _ in range(300)}
    assert hours == set(range(9, 22))


def test_bump_due() -> None:
    listing_id = uuid4()
    hour = bump_hour(listing_id)
    at_hour = datetime(2026, 10, 3, hour - 4, 5, tzinfo=UTC)  # Тбилиси = UTC+4
    until = at_hour + timedelta(days=10)
    assert bump_due(listing_id, until, None, at_hour)
    assert not bump_due(listing_id, until, None, at_hour - timedelta(hours=1)), "ещё не его час"
    assert not bump_due(listing_id, until, at_hour - timedelta(hours=3), at_hour), "уже сегодня"
    assert bump_due(listing_id, until, at_hour - timedelta(days=1), at_hour)
    assert not bump_due(listing_id, at_hour - timedelta(minutes=1), None, at_hour), "истёк"


def test_bump_payload_round_trip() -> None:
    listing_id = uuid4()
    assert listing_from_bump_payload(f"bump:{listing_id}") == listing_id
    assert listing_from_bump_payload("bump:nope") is None
    assert listing_from_bump_payload(f"promo:{listing_id}") is None
