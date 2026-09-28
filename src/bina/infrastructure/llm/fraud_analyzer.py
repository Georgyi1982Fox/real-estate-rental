"""AI-проверка объявлений на мошенничество через LLM (AITUNNEL) — TASK-011.

Как и переводчик: обычный ``complete`` и JSON в ответе, проверка Pydantic,
при кривом ответе — ещё попытка с уточнением.
"""

import json
import re

import httpx
import structlog
from pydantic import BaseModel, Field, ValidationError

from bina.application.ports.fraud import (
    AI_REASONS,
    FraudAnalysisError,
    FraudVerdict,
    IFraudAnalyzer,
    ListingFacts,
)
from bina.application.ports.llm_provider import LLMProvider
from bina.application.ports.translator import ListingText
from bina.infrastructure.llm.prompts.detect_fraud import build_fraud_prompt

logger = structlog.get_logger(__name__)

JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class _Verdict(BaseModel):
    score: int = Field(ge=0, le=100)
    reasons: list[str] = []


def parse_verdict(raw: str) -> FraudVerdict:
    """Разбирает ответ модели; ``ValueError``, если это не нужный JSON.

    Неизвестные коды причин отбрасываются (модель иногда придумывает свои).
    """
    match = JSON_OBJECT_RE.search(raw)
    if match is None:
        raise ValueError("no JSON object in the response")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    try:
        verdict = _Verdict.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid verdict: {exc}") from exc
    reasons = [code for code in dict.fromkeys(verdict.reasons) if code in AI_REASONS]
    return FraudVerdict(score=verdict.score, reasons=reasons)


class LLMFraudAnalyzer(IFraudAnalyzer):
    """:class:`IFraudAnalyzer` поверх :class:`LLMProvider`."""

    def __init__(self, provider: LLMProvider, attempts: int = 2) -> None:
        self._provider = provider
        self._attempts = attempts

    async def analyze(self, text: ListingText, facts: ListingFacts) -> FraudVerdict:
        """Оценка одним запросом."""
        prompt = build_fraud_prompt(text, facts)
        last_error = ""
        for attempt in range(1, self._attempts + 1):
            try:
                raw = await self._provider.complete(prompt)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise FraudAnalysisError(f"LLM request failed: {exc}") from exc
            try:
                return parse_verdict(raw)
            except ValueError as exc:
                last_error = str(exc)
                logger.warning("Bad fraud response", attempt=attempt, error=last_error)
                prompt += "\n\nYour previous reply was not valid. Reply with the JSON object only."
        raise FraudAnalysisError(f"invalid LLM response: {last_error}")
