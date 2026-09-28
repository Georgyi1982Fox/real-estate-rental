"""LLMFraudAnalyzer: промпт, разбор ответа, повтор и ошибки (без сети)."""

from decimal import Decimal
from typing import Any

import httpx
import pytest

from bina.application.ports.fraud import FraudAnalysisError, FraudVerdict, ListingFacts
from bina.application.ports.llm_provider import LLMProvider
from bina.application.ports.translator import ListingText
from bina.infrastructure.llm.fraud_analyzer import LLMFraudAnalyzer, parse_verdict
from bina.infrastructure.llm.prompts.detect_fraud import build_fraud_prompt


class FakeProvider(LLMProvider):
    def __init__(self, replies: list[str | Exception]) -> None:
        self.replies = replies
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    async def complete_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


TEXT = ListingText("Квартира в Ваке", "Хозяин за границей, переведите залог на карту")
FACTS = ListingFacts(
    price=Decimal(300),
    currency="USD",
    rooms=3,
    area=Decimal(100),
    district="Vake",
    photos=0,
    district_median_per_m2=Decimal(15),
)


def test_prompt_has_text_facts_and_codes() -> None:
    prompt = build_fraud_prompt(TEXT, FACTS)
    assert TEXT.title in prompt and TEXT.description in prompt
    assert "3.0 USD/m²" in prompt and "15.0 USD/m²" in prompt
    assert '"prepayment"' in prompt and '"owner_abroad"' in prompt
    assert "Photos: 0" in prompt


def test_prompt_without_median() -> None:
    prompt = build_fraud_prompt(TEXT, FraudFactsNoMedian)
    assert "District median price: unknown" in prompt


FraudFactsNoMedian = ListingFacts(
    price=Decimal(1000), currency="GEL", rooms=2, area=Decimal(50), district="", photos=3
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            '{"score": 85, "reasons": ["prepayment", "owner_abroad"]}',
            FraudVerdict(85, ["prepayment", "owner_abroad"]),
        ),
        ('```json\n{"score": 10, "reasons": []}\n```', FraudVerdict(10, [])),
        # Выдуманные коды и повторы отбрасываются
        (
            '{"score": 50, "reasons": ["urgency", "bad_vibes", "urgency"]}',
            FraudVerdict(50, ["urgency"]),
        ),
        ('{"score": 0}', FraudVerdict(0, [])),
    ],
)
def test_parse_verdict(raw: str, expected: FraudVerdict) -> None:
    assert parse_verdict(raw) == expected


@pytest.mark.parametrize("raw", ["no json", '{"score": 150}', '{"score": "high"}', "[1, 2]"])
def test_parse_verdict_rejects(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_verdict(raw)


async def test_retry_after_bad_reply() -> None:
    provider = FakeProvider(["sorry", '{"score": 90, "reasons": ["prepayment"]}'])
    verdict = await LLMFraudAnalyzer(provider).analyze(TEXT, FACTS)
    assert verdict == FraudVerdict(90, ["prepayment"])
    assert "previous reply was not valid" in provider.prompts[1]


async def test_errors() -> None:
    with pytest.raises(FraudAnalysisError, match="invalid LLM response"):
        await LLMFraudAnalyzer(FakeProvider(["x", "y"])).analyze(TEXT, FACTS)
    request = httpx.Request("POST", "https://api.aitunnel.ru/v1/chat/completions")
    failure = httpx.HTTPStatusError("400", request=request, response=httpx.Response(400))
    with pytest.raises(FraudAnalysisError, match="LLM request failed"):
        await LLMFraudAnalyzer(FakeProvider([failure])).analyze(TEXT, FACTS)
