"""LLMTranslator: промпт, разбор ответа модели, повтор и ошибки (без сети)."""

import json
from typing import Any

import httpx
import pytest

from bina.application.ports.llm_provider import LLMProvider
from bina.application.ports.translator import ListingText, TranslationError
from bina.infrastructure.llm.translator import LLMTranslator, build_prompt, parse_response

TEXT = ListingText("Сдается 2 комнатная квартира в ваке", "Ремонт, 60 м², 1500 ₾")
GOOD = {
    "ka": {"title": "ქირავდება 2-ოთახიანი ბინა ვაკეში", "description": "რემონტი, 60 მ², 1500 ₾"},
    "en": {"title": "2-room apartment for rent in Vake", "description": "Renovated, 60 m², 1500 ₾"},
}


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


def test_prompt_mentions_languages_and_text() -> None:
    prompt = build_prompt(TEXT, "ru", ["ka", "en"])
    assert "from Russian" in prompt
    assert '"ka" (Georgian)' in prompt and '"en" (English)' in prompt
    assert TEXT.title in prompt and TEXT.description in prompt


def test_parse_response_accepts_markdown_fence() -> None:
    raw = "```json\n" + json.dumps(GOOD, ensure_ascii=False) + "\n```"
    result = parse_response(raw, ["ka", "en"])
    assert result["ka"] == ListingText(GOOD["ka"]["title"], GOOD["ka"]["description"])
    assert result["en"].title == "2-room apartment for rent in Vake"


@pytest.mark.parametrize(
    "raw",
    [
        "Sorry, I can't",
        "{not json}",
        json.dumps({"ka": GOOD["ka"]}),  # нет en
        json.dumps({"ka": GOOD["ka"], "en": {"title": " ", "description": ""}}),
    ],
)
def test_parse_response_rejects_incomplete(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_response(raw, ["ka", "en"])


async def test_translate_retries_after_bad_reply() -> None:
    provider = FakeProvider(["no json here", json.dumps(GOOD, ensure_ascii=False)])

    result = await LLMTranslator(provider).translate(TEXT, "ru", ["ka", "en"])

    assert set(result) == {"ka", "en"}
    assert len(provider.prompts) == 2
    assert "not valid" in provider.prompts[1]


async def test_translate_gives_up() -> None:
    provider = FakeProvider(["nope", "still nope"])
    with pytest.raises(TranslationError, match="invalid LLM response"):
        await LLMTranslator(provider).translate(TEXT, "ru", ["ka"])


async def test_http_error_becomes_translation_error() -> None:
    provider = FakeProvider([httpx.ConnectError("offline")])
    with pytest.raises(TranslationError, match="LLM request failed"):
        await LLMTranslator(provider).translate(TEXT, "ru", ["en"])


async def test_unknown_language_and_no_targets() -> None:
    translator = LLMTranslator(FakeProvider([]))
    with pytest.raises(TranslationError, match="unsupported"):
        await translator.translate(TEXT, "ru", ["de"])
    assert await translator.translate(TEXT, "ru", []) == {}
