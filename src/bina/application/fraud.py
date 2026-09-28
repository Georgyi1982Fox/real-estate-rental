"""Политика антифрода: правила, итоговый балл и уровни (TASK-011).

Итоговый балл = балл AI + баллы правил (не больше 100). Правила сами по себе
дают не больше 50 — только предупреждение: скрыть объявление может лишь
AI вместе с правилами или AI с очень уверенной оценкой.
"""

from decimal import Decimal
from enum import StrEnum

from bina.application.ports.fraud import FraudVerdict, ListingFacts

# Предупреждение ⚠️ в карточке
WARNING_SCORE = 40
# Скрыть из поиска и уведомлений (по прямой ссылке объявление открывается)
HIDE_SCORE = 80

# Цена за м² ниже этой доли медианы района — подозрительно
FAR_BELOW_RATIO = Decimal("0.4")
BELOW_RATIO = Decimal("0.6")
FAR_BELOW_POINTS = 40
BELOW_POINTS = 20
NO_PHOTOS_POINTS = 10
MAX_SCORE = 100


class FraudLevel(StrEnum):
    """Уровень для интерфейса."""

    NONE = "none"
    WARNING = "warning"
    HIGH = "high"


def fraud_level(score: int) -> FraudLevel:
    """Уровень по итоговому баллу."""
    if score >= HIDE_SCORE:
        return FraudLevel.HIGH
    if score >= WARNING_SCORE:
        return FraudLevel.WARNING
    return FraudLevel.NONE


def rule_signals(facts: ListingFacts) -> FraudVerdict:
    """Признаки, которые видны без AI: цена сильно ниже рынка, нет фото."""
    score = 0
    reasons: list[str] = []
    median = facts.district_median_per_m2
    if median is not None and median > 0 and facts.area > 0:
        ratio = facts.price / facts.area / median
        if ratio < FAR_BELOW_RATIO:
            score += FAR_BELOW_POINTS
            reasons.append("price_far_below_market")
        elif ratio < BELOW_RATIO:
            score += BELOW_POINTS
            reasons.append("price_far_below_market")
    if facts.photos == 0:
        score += NO_PHOTOS_POINTS
        reasons.append("no_photos")
    return FraudVerdict(score=score, reasons=reasons)


def combine(ai: FraudVerdict, rules: FraudVerdict) -> FraudVerdict:
    """Итог: сумма баллов (не больше 100), причины без повторов (сначала AI)."""
    reasons = list(dict.fromkeys([*ai.reasons, *rules.reasons]))
    return FraudVerdict(score=min(MAX_SCORE, ai.score + rules.score), reasons=reasons)
