"""AI-помощник арендатора через LLM (AITUNNEL) — TASK-095.

Как антифрод и разбор постов: обычный ``complete``, JSON в ответе, проверка
Pydantic, при кривом ответе — ещё попытка с уточнением.
"""

import json
import re

import httpx
import structlog
from pydantic import BaseModel, Field, ValidationError

from bina.application.ports.assistant import (
    AssistantError,
    IAssistant,
    ListingBrief,
    OwnerMessage,
)
from bina.application.ports.llm_provider import LLMProvider
from bina.infrastructure.llm.prompts.assistant import (
    build_owner_message_prompt,
    build_viewing_questions_prompt,
)

logger = structlog.get_logger(__name__)

JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
MAX_QUESTIONS = 8


class _OwnerMessage(BaseModel):
    text_ka: str = Field(min_length=10)
    translation: str = Field(min_length=10)


class _Questions(BaseModel):
    questions: list[str] = Field(min_length=3)


def parse_json[T: BaseModel](raw: str, model: type[T]) -> T:
    """JSON-объект из ответа модели; ``ValueError``, если он не такой."""
    match = JSON_OBJECT_RE.search(raw)
    if match is None:
        raise ValueError("no JSON object in the response")
    try:
        return model.model_validate(json.loads(match.group(0)))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"invalid response: {exc}") from exc


class LLMAssistant(IAssistant):
    """:class:`IAssistant` поверх :class:`LLMProvider`."""

    def __init__(self, provider: LLMProvider, attempts: int = 2) -> None:
        self._provider = provider
        self._attempts = attempts

    async def message_owner(self, listing: ListingBrief, language: str, note: str) -> OwnerMessage:
        prompt = build_owner_message_prompt(listing, language, note)
        result = await self._ask(prompt, _OwnerMessage)
        return OwnerMessage(text_ka=result.text_ka.strip(), translation=result.translation.strip())

    async def viewing_questions(self, listing: ListingBrief, language: str, note: str) -> list[str]:
        prompt = build_viewing_questions_prompt(listing, language, note)
        result = await self._ask(prompt, _Questions)
        questions = [q.strip().lstrip("-•0123456789.) ").strip() for q in result.questions]
        return [q for q in questions if q][:MAX_QUESTIONS]

    async def close(self) -> None:
        """Закрывает HTTP-клиент провайдера (если есть)."""
        close = getattr(self._provider, "close", None)
        if close is not None:
            await close()

    async def _ask[T: BaseModel](self, prompt: str, model: type[T]) -> T:
        last_error = ""
        for attempt in range(1, self._attempts + 1):
            try:
                raw = await self._provider.complete(prompt)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise AssistantError(f"LLM request failed: {exc}") from exc
            try:
                return parse_json(raw, model)
            except ValueError as exc:
                last_error = str(exc)
                logger.warning("Bad assistant response", attempt=attempt, error=last_error)
                prompt += "\n\nYour previous reply was not valid. Reply with the JSON object only."
        raise AssistantError(f"invalid LLM response: {last_error}")
