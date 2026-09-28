"""Политика антифрода: правила, сумма баллов, уровни (TASK-011)."""

from decimal import Decimal

import pytest

from bina.application.fraud import FraudLevel, combine, fraud_level, rule_signals
from bina.application.ports.fraud import FraudVerdict, ListingFacts


def facts(price: int, area: int = 50, median: int | None = 20, photos: int = 5) -> ListingFacts:
    return ListingFacts(
        price=Decimal(price),
        currency="USD",
        rooms=2,
        area=Decimal(area),
        district="Vake",
        photos=photos,
        district_median_per_m2=None if median is None else Decimal(median),
    )


@pytest.mark.parametrize(
    ("price", "median", "photos", "score", "reasons"),
    [
        (1000, 20, 5, 0, []),  # 20/м² — как медиана
        (550, 20, 5, 20, ["price_far_below_market"]),  # 11/м² — 55% медианы
        (350, 20, 5, 40, ["price_far_below_market"]),  # 7/м² — 35% медианы
        (350, None, 5, 0, []),  # медианы нет — не сравниваем
        (1000, 20, 0, 10, ["no_photos"]),
        (350, 20, 0, 50, ["price_far_below_market", "no_photos"]),
    ],
)
def test_rule_signals(
    price: int, median: int | None, photos: int, score: int, reasons: list[str]
) -> None:
    verdict = rule_signals(facts(price, median=median, photos=photos))
    assert (verdict.score, verdict.reasons) == (score, reasons)


def test_rules_alone_never_hide() -> None:
    worst = rule_signals(facts(10, median=20, photos=0))
    assert fraud_level(worst.score) is FraudLevel.WARNING


def test_combine_caps_and_dedupes() -> None:
    ai = FraudVerdict(70, ["prepayment", "urgency"])
    rules = FraudVerdict(50, ["price_far_below_market", "no_photos"])
    assert combine(ai, rules) == FraudVerdict(
        100, ["prepayment", "urgency", "price_far_below_market", "no_photos"]
    )
    assert combine(FraudVerdict(0, []), FraudVerdict(0, [])) == FraudVerdict(0, [])


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0, FraudLevel.NONE),
        (39, FraudLevel.NONE),
        (40, FraudLevel.WARNING),
        (79, FraudLevel.WARNING),
        (80, FraudLevel.HIGH),
    ],
)
def test_levels(score: int, level: FraudLevel) -> None:
    assert fraud_level(score) is level
