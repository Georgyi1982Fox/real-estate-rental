"""Переводчик объявлений через LLM (AITUNNEL, OpenAI-совместимый API) — TASK-010.

Модель получает текст и отвечает JSON-ом ``{"ka": {"title": ..., "description": ...}, ...}``.
Используется обычный ``complete`` (без tool calling): так работает с любой моделью
провайдера. Ответ проверяется Pydantic; при ошибке — ещё попытка с уточнением.
"""

import json
import re
from collections.abc import Sequence

import httpx
import structlog
from pydantic import BaseModel, ValidationError

from bina.application.localization import in_language
from bina.application.ports.llm_provider import LLMProvider
from bina.application.ports.translator import (
    IMessageTranslator,
    ITranslator,
    ListingText,
    TranslationError,
)

logger = structlog.get_logger(__name__)

LANGUAGE_NAMES = {"ru": "Russian", "ka": "Georgian", "en": "English"}
# Длинные описания обрезаем: перевод объявлений, а не романов (и дешевле)
MAX_DESCRIPTION_CHARS = 3000
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class _TranslatedText(BaseModel):
    title: str
    description: str = ""


def build_prompt(text: ListingText, source: str, targets: Sequence[str]) -> str:
    """Промпт перевода объявления."""
    target_list = ", ".join(f'"{code}" ({LANGUAGE_NAMES[code]})' for code in targets)
    example = ", ".join(f'"{code}": {{"title": "...", "description": "..."}}' for code in targets)
    description = text.description[:MAX_DESCRIPTION_CHARS]
    return f"""You translate apartment rental listings from Georgia (Tbilisi, Batumi).
Translate the listing below from {LANGUAGE_NAMES[source]} to: {target_list}.

Rules:
- Natural, idiomatic phrasing a local would use in a rental ad; Georgian in Georgian script.
- Keep numbers, prices, currencies, areas, floors, phone numbers and URLs exactly as they are.
- Street, district and metro names: use the usual spelling in the target language.
- Keep line breaks. Do not add or drop information, do not comment.
- If the description is empty, return an empty description.

Reply with ONLY a JSON object, no markdown, in this shape:
{{{example}}}

Title:
{text.title}

Description:
{description}
"""


def parse_response(raw: str, targets: Sequence[str]) -> dict[str, ListingText]:
    """Разбирает ответ модели; ``ValueError``, если он неполный или не JSON."""
    match = JSON_OBJECT_RE.search(raw)
    if match is None:
        raise ValueError("no JSON object in the response")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("response is not a JSON object")

    result: dict[str, ListingText] = {}
    for code in targets:
        try:
            item = _TranslatedText.model_validate(data.get(code))
        except ValidationError as exc:
            raise ValueError(f"missing or invalid {code!r} translation") from exc
        if not item.title.strip():
            raise ValueError(f"empty {code!r} title")
        # Модель иногда оставляет текст на языке оригинала: такой «перевод» не сохраняем,
        # иначе грузин навсегда увидит русское описание
        for part in (item.title, item.description):
            if not in_language(part, code):
                raise ValueError(f"{code!r} translation is not in {LANGUAGE_NAMES[code]}")
        result[code] = ListingText(item.title.strip(), item.description.strip())
    return result


class LLMTranslator(ITranslator):
    """:class:`ITranslator` поверх :class:`LLMProvider`."""

    def __init__(self, provider: LLMProvider, attempts: int = 2) -> None:
        self._provider = provider
        self._attempts = attempts

    async def translate(
        self,
        text: ListingText,
        source: str,
        targets: Sequence[str],
    ) -> dict[str, ListingText]:
        """Перевод на все ``targets`` одним запросом."""
        unknown = [code for code in (source, *targets) if code not in LANGUAGE_NAMES]
        if unknown:
            raise TranslationError(f"unsupported languages: {unknown}")
        if not targets:
            return {}

        prompt = build_prompt(text, source, targets)
        last_error = ""
        for attempt in range(1, self._attempts + 1):
            try:
                raw = await self._provider.complete(prompt)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise TranslationError(f"LLM request failed: {exc}") from exc
            try:
                return parse_response(raw, targets)
            except ValueError as exc:
                last_error = str(exc)
                logger.warning("Bad translation response", attempt=attempt, error=last_error)
                prompt += (
                    f"\n\nYour previous reply was not valid ({last_error}). Every value must "
                    "be written in its target language and script. Reply with the JSON object only."
                )
        raise TranslationError(f"invalid LLM response: {last_error}")


class _TranslatedMessage(BaseModel):
    text: str


def build_message_prompt(text: str, target: str) -> str:
    """Промпт перевода сообщения чата (TASK-111)."""
    return f"""You translate chat messages between a tenant and a landlord about renting
an apartment in Georgia. Translate the message below to {LANGUAGE_NAMES[target]}.

Rules:
- Natural, polite, conversational phrasing; Georgian in Georgian script.
- Keep numbers, prices, dates, times, addresses, phone numbers and URLs exactly as they are.
- If the message is already in {LANGUAGE_NAMES[target]}, return it unchanged.
- Translate only. Do not answer the message, do not add or drop information.

Reply with ONLY a JSON object, no markdown: {{"text": "..."}}

Message:
{text}
"""


class LLMMessageTranslator(IMessageTranslator):
    """:class:`IMessageTranslator` поверх :class:`LLMProvider`."""

    def __init__(self, provider: LLMProvider, attempts: int = 2) -> None:
        self._provider = provider
        self._attempts = attempts

    async def translate_message(self, text: str, target: str) -> str:
        if target not in LANGUAGE_NAMES:
            raise TranslationError(f"unsupported language: {target}")
        prompt = build_message_prompt(text, target)
        last_error = ""
        for attempt in range(1, self._attempts + 1):
            try:
                raw = await self._provider.complete(prompt)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise TranslationError(f"LLM request failed: {exc}") from exc
            match = JSON_OBJECT_RE.search(raw)
            try:
                if match is None:
                    raise ValueError("no JSON object in the response")
                result = _TranslatedMessage.model_validate(json.loads(match.group(0)))
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = str(exc)
                logger.warning("Bad message translation", attempt=attempt, error=last_error)
                prompt += "\n\nYour previous reply was not valid. Reply with the JSON object only."
                continue
            if result.text.strip() and in_language(result.text, target):
                return result.text.strip()
            last_error = "empty translation" if not result.text.strip() else "wrong language"
            prompt += f"\n\nReply in {LANGUAGE_NAMES[target]} only."
        raise TranslationError(f"invalid LLM response: {last_error}")

    async def close(self) -> None:
        """Закрывает HTTP-клиент провайдера (если есть)."""
        close = getattr(self._provider, "close", None)
        if close is not None:
            await close()
