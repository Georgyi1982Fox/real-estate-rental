"""Перевод объявлений на недостающие языки (без AI и базы)."""

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

from bina.application.ports.translator import ITranslator, ListingText, TranslationError
from bina.application.use_cases.translate_listings import (
    TranslateListingsUseCase,
    missing_languages,
    source_language,
)
from bina.infrastructure.db.models import Listing


def listing(**texts: str) -> Listing:
    values = {
        f"{field}_{code}": "" for field in ("title", "description") for code in ("ru", "ka", "en")
    }
    values.update(texts)
    return cast(Listing, SimpleNamespace(id=uuid4(), **values))


class FakeTranslator(ITranslator):
    def __init__(self, fail_titles: Sequence[str] = ()) -> None:
        self.calls: list[tuple[ListingText, str, list[str]]] = []
        self.fail_titles = set(fail_titles)

    async def translate(
        self, text: ListingText, source: str, targets: Sequence[str]
    ) -> dict[str, ListingText]:
        self.calls.append((text, source, list(targets)))
        if text.title in self.fail_titles:
            raise TranslationError("boom")
        return {
            code: ListingText(f"{code}:{text.title}", f"{code}:{text.description}")
            for code in targets
        }


class FakeRepository:
    def __init__(self, listings: list[Listing]) -> None:
        self.listings = listings
        self.saved: dict[UUID, dict[str, ListingText]] = {}
        self.limits: list[int] = []
        self.failed: list[UUID] = []

    async def list_untranslated(self, limit: int) -> list[Listing]:
        self.limits.append(limit)
        return self.listings[:limit]

    async def save_texts(self, listing_id: UUID, texts: dict[str, ListingText]) -> None:
        self.saved[listing_id] = texts

    async def mark_translation_failed(self, listing_id: UUID) -> None:
        self.failed.append(listing_id)


def test_source_and_missing_languages() -> None:
    ru_only = listing(title_ru="Квартира", description_ru="Описание")
    assert source_language(ru_only) == "ru"
    assert missing_languages(ru_only) == ["ka", "en"]

    ka_and_en = listing(title_ka="ბინა", title_en="Flat")
    assert source_language(ka_and_en) == "ka"
    assert missing_languages(ka_and_en) == ["ru"]

    empty = listing()
    assert source_language(empty) is None


async def test_translates_missing_languages_from_russian() -> None:
    item = listing(title_ru=" Квартира ", description_ru="Описание")
    translator = FakeTranslator()
    repository = FakeRepository([item])

    stats = await TranslateListingsUseCase(translator, repository).execute(limit=5)

    assert (stats.checked, stats.translated, stats.failed) == (1, 1, 0)
    assert repository.limits == [5]
    assert translator.calls == [(ListingText("Квартира", "Описание"), "ru", ["ka", "en"])]
    assert repository.saved[item.id] == {
        "ka": ListingText("ka:Квартира", "ka:Описание"),
        "en": ListingText("en:Квартира", "en:Описание"),
    }


async def test_failure_does_not_stop_other_listings() -> None:
    broken = listing(title_ru="Сломанное")
    good = listing(title_ru="Хорошее")
    done = listing(title_ru="Готово", title_ka="მზადაა", title_en="Done")
    nothing = listing()
    repository = FakeRepository([broken, good, done, nothing])

    stats = await TranslateListingsUseCase(
        FakeTranslator(fail_titles=["Сломанное"]), cast(Any, repository)
    ).execute(limit=10)

    assert (stats.checked, stats.translated, stats.failed) == (4, 1, 1)
    assert list(repository.saved) == [good.id]
    # Неудачное отложено на сутки — не загораживает остальные в следующих запусках
    assert repository.failed == [broken.id]
