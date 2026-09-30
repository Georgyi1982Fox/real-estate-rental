"""Умный поиск: текст объявления, отпечатки, выдача (TASK-012)."""

from collections.abc import Sequence
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.ports.embeddings import EmbeddingsError
from bina.application.semantic_search import SMART_LIMIT, is_smart_query, listing_text
from bina.application.use_cases.embed_listings import EmbedListingsUseCase
from bina.application.use_cases.smart_search import SmartSearchUseCase
from bina.infrastructure.db.models import Listing
from tests.support.embeddings import FakeEmbedder


def listing(**fields: Any) -> Listing:
    base: dict[str, Any] = {
        "id": uuid4(),
        "title_en": "Sunny flat",
        "title_ru": "Солнечная квартира",
        "title_ka": "",
        "description_en": "Near the metro, with a balcony.",
        "description_ru": "",
        "description_ka": "",
        "rooms": 2,
        "area": Decimal("60.0"),
        "price": Decimal("1200"),
        "currency": "GEL",
        "rent_period": "monthly",
        "floor": 5,
        "condition": "newly_renovated",
        "features": ["balcony", "air_conditioning"],
        "district": SimpleNamespace(name_en="Vake", city="tbilisi"),
    }
    base.update(fields)
    return cast(Listing, SimpleNamespace(**base))


def test_listing_text() -> None:
    text = listing_text(listing())
    assert text.startswith("2-room apartment for rent. 60 m². 1200 GEL per month. Vake, Tbilisi")
    assert "floor 5" in text
    assert "newly renovated" in text
    assert "balcony, air conditioning" in text
    assert "Sunny flat" in text
    assert "Near the metro" in text


def test_listing_text_falls_back_to_russian() -> None:
    text = listing_text(listing(title_en="", description_en="", description_ru="У метро"))
    assert "Солнечная квартира" in text
    assert "У метро" in text


def test_is_smart_query() -> None:
    assert is_smart_query("балкон")
    assert not is_smart_query("ок")
    assert not is_smart_query("1500")
    assert not is_smart_query(None)


class FakeRepository:
    def __init__(self, listings: list[Listing]) -> None:
        self.listings = listings
        self.saved: list[UUID] = []

    async def to_embed(self, limit: int, model: str) -> list[Listing]:
        return self.listings[:limit]

    async def save_many(self, vectors: Sequence[tuple[UUID, list[float]]], model: str) -> None:
        self.saved += [listing_id for listing_id, _ in vectors]


class FlakyEmbedder(FakeEmbedder):
    """Первая пачка проходит, дальше сервис падает."""

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self.calls:
            raise EmbeddingsError("rate limit")
        return await super().embed(texts)


async def test_embed_in_batches() -> None:
    items = [listing() for _ in range(5)]
    repository = FakeRepository(items)
    embedder = FakeEmbedder()

    stats = await EmbedListingsUseCase(repository, embedder, batch_size=2).execute(10)

    assert (stats.checked, stats.embedded, stats.failed) == (5, 5, 0)
    assert [len(call) for call in embedder.calls] == [2, 2, 1]
    assert repository.saved == [item.id for item in items]


async def test_embed_failure_later_is_deferred() -> None:
    repository = FakeRepository([listing() for _ in range(5)])
    stats = await EmbedListingsUseCase(repository, FlakyEmbedder(), batch_size=2).execute(10)
    assert (stats.embedded, stats.failed) == (2, 3)


async def test_embed_failure_at_start_is_reported() -> None:
    repository = FakeRepository([listing()])
    with pytest.raises(EmbeddingsError):
        await EmbedListingsUseCase(repository, FakeEmbedder(fail=True)).execute(10)


class FakeSemanticRepository:
    def __init__(self, count: int) -> None:
        self.count = count
        self.calls: list[tuple[ListingSearchFilters, int, int]] = []

    async def semantic_search(
        self,
        filters: ListingSearchFilters,
        vector: list[float],
        model: str,
        limit: int,
        offset: int = 0,
    ) -> list[Listing]:
        self.calls.append((filters, limit, offset))
        return [listing() for _ in range(limit)]

    async def semantic_count(self, filters: ListingSearchFilters, model: str) -> int:
        return self.count


async def test_smart_search_caps_results() -> None:
    repository = FakeSemanticRepository(count=500)
    use_case = SmartSearchUseCase(repository, FakeEmbedder())
    filters = ListingSearchFilters(query="балкон", rooms_min=2)

    page = await use_case.execute(filters, page=0, page_size=20)
    assert page.total == SMART_LIMIT
    [(used, limit, offset)] = repository.calls
    assert used.query is None, "слова не обязаны совпадать"
    assert used.rooms_min == 2
    assert (limit, offset) == (20, 0)

    last = await use_case.execute(filters, page=2, page_size=20)
    assert len(last.items) == SMART_LIMIT - 40
    beyond = await use_case.execute(filters, page=3, page_size=20)
    assert beyond.items == []
