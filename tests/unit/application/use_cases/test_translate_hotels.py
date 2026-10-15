"""Перевод описаний гостиниц на недостающие языки (без AI и базы)."""

from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

from bina.application.ports.translator import IMessageTranslator, TranslationError
from bina.application.use_cases.translate_hotels import (
    TranslateHotelsUseCase,
    description_language,
    missing_languages,
)
from bina.infrastructure.db.models import Hotel


def hotel(**descriptions: str) -> Hotel:
    values = {f"description_{code}": "" for code in ("ru", "ka", "en")}
    values.update(descriptions)
    return cast(Hotel, SimpleNamespace(id=uuid4(), **values))


class FakeTranslator(IMessageTranslator):
    def __init__(self, fail_texts: tuple[str, ...] = ()) -> None:
        self.calls: list[tuple[str, str]] = []
        self.fail_texts = set(fail_texts)

    async def translate_message(self, text: str, target: str) -> str:
        self.calls.append((text, target))
        if text in self.fail_texts:
            raise TranslationError("boom")
        return f"{text} [{target}]"


class FakeRepository:
    def __init__(self, hotels: list[Hotel]) -> None:
        self.hotels = hotels
        self.saved: dict[UUID, dict[str, str]] = {}

    async def list_untranslated(self, limit: int) -> list[Hotel]:
        return self.hotels[:limit]

    async def save_descriptions(self, hotel_id: UUID, by_language: dict[str, str]) -> None:
        self.saved[hotel_id] = by_language


def test_description_language_and_missing() -> None:
    one = hotel(description_ru="Уютная квартира у моря")
    assert description_language(one) == "ru"
    assert missing_languages(one) == ["ka", "en"]
    full = hotel(description_ru="ru", description_ka="ka", description_en="en")
    assert missing_languages(full) == []


async def test_translates_missing_descriptions() -> None:
    subject = hotel(description_ka="ზღვისპირა სასტუმრო")
    repository = FakeRepository([subject])
    translator = FakeTranslator()
    use_case = TranslateHotelsUseCase(translator, repository)

    stats = await use_case.execute(10)

    assert (stats.checked, stats.translated, stats.failed) == (1, 1, 0)
    assert repository.saved[subject.id] == {
        "ru": "ზღვისპირა სასტუმრო [ru]",
        "en": "ზღვისპირა სასტუმრო [en]",
    }
    # Переводим с языка, на котором ввёл хозяин
    assert {target for _, target in translator.calls} == {"ru", "en"}


async def test_fully_translated_and_empty_are_skipped() -> None:
    full = hotel(description_ru="ru", description_ka="ka", description_en="en")
    blank = hotel()
    repository = FakeRepository([full, blank])
    translator = FakeTranslator()

    stats = await TranslateHotelsUseCase(translator, repository).execute(10)

    assert (stats.translated, stats.failed) == (0, 0)
    assert translator.calls == []
    assert repository.saved == {}


async def test_failure_does_not_save() -> None:
    subject = hotel(description_en="Seaside apartment")
    repository = FakeRepository([subject])
    translator = FakeTranslator(fail_texts=("Seaside apartment",))

    stats = await TranslateHotelsUseCase(translator, repository).execute(10)

    assert (stats.checked, stats.translated, stats.failed) == (1, 0, 1)
    assert repository.saved == {}
