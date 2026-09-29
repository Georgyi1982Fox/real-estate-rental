"""AI-помощник (TASK-095): промпты и разбор ответов, без сети."""

import pytest

from bina.application.ports.assistant import AssistantError, ListingBrief
from bina.application.ports.llm_provider import LLMProvider
from bina.infrastructure.llm.assistant import LLMAssistant
from bina.infrastructure.llm.prompts.assistant import (
    build_owner_message_prompt,
    build_viewing_questions_prompt,
)

BRIEF = ListingBrief(
    title="2-комн. квартира в Ваке",
    description="Светлая квартира, новый ремонт, центральное отопление.",
    price="1500 GEL",
    rooms=2,
    area=60.0,
    district="Vake",
    floor=5,
    total_floors=9,
    features=["furniture", "air_conditioning"],
)


class FakeProvider(LLMProvider):
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.replies.pop(0)

    async def complete_structured(self, prompt: str, schema: dict) -> dict:  # type: ignore[type-arg]
        raise NotImplementedError


def test_prompts_contain_listing_and_note() -> None:
    owner = build_owner_message_prompt(BRIEF, "ru", "двое, с кошкой")
    assert "IN GEORGIAN" in owner and "Russian" in owner
    assert "Vake" in owner and "1500 GEL" in owner and "5/9" in owner
    assert "двое, с кошкой" in owner
    questions = build_viewing_questions_prompt(BRIEF, "en", "")
    assert "English" in questions and "heating" in questions
    assert "About the tenant: nothing." in questions


async def test_message_owner() -> None:
    provider = FakeProvider(
        [
            '```json\n{"text_ka": "გამარჯობა, მაინტერესებს ბინა ვაკეში.", '
            '"translation": "Здравствуйте, меня интересует квартира в Ваке."}\n```'
        ]
    )
    message = await LLMAssistant(provider).message_owner(BRIEF, "ru", "")
    assert message.text_ka.startswith("გამარჯობა")
    assert message.translation.startswith("Здравствуйте")


async def test_viewing_questions_cleaned_and_limited() -> None:
    items = ", ".join(f'"{n}. Вопрос {n}?"' for n in range(1, 11))
    provider = FakeProvider(["not json", f'{{"questions": [{items}]}}'])
    questions = await LLMAssistant(provider).viewing_questions(BRIEF, "ru", "")
    assert questions[0] == "Вопрос 1?"
    assert len(questions) == 8
    assert "not valid" in provider.prompts[1], "повтор с уточнением"


async def test_bad_answers_raise() -> None:
    provider = FakeProvider(["nope", '{"questions": []}'])
    with pytest.raises(AssistantError):
        await LLMAssistant(provider).viewing_questions(BRIEF, "ru", "")
