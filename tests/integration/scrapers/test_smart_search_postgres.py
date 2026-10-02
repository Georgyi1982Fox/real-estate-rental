"""Умный поиск на PostgreSQL + pgvector (TASK-012)."""

import dataclasses
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.ports.scraper import RawListing
from bina.application.use_cases.embed_listings import EmbedListingsUseCase
from bina.application.use_cases.smart_search import SmartSearchUseCase
from bina.infrastructure.db.models import Embedding
from bina.infrastructure.db.repositories.embeddings import EmbeddingsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.embeddings import FakeEmbedder


def flat(source_id: str, text: str, **fields: Any) -> RawListing:
    # Заголовок собирается из данных, смысл объявления — в описании
    base = RawListing(
        source_id=source_id,
        source_name="ss",
        title="Квартира",
        description=text,
        price=1000.0,
        currency="GEL",
        rooms=2,
        area=60.0,
        district="Ваке",
        url=f"https://ss.example/{source_id}",
    )
    return dataclasses.replace(base, **fields)


async def test_embed_and_search_by_meaning(session: AsyncSession) -> None:
    listings = ListingsRepository(session)
    await listings.create_or_update_from_raw(flat("1", "Квартира у метро"))
    await listings.create_or_update_from_raw(flat("2", "Квартира с балконом"))
    await listings.create_or_update_from_raw(flat("3", "Квартира с видом на море", city="batumi"))
    await listings.create_or_update_from_raw(flat("4", "Дорогой балкон", price=5000.0))
    await session.commit()
    embedder = FakeEmbedder()
    embeddings = EmbeddingsRepository(session)

    stats = await EmbedListingsUseCase(embeddings, embedder).execute(100)
    await session.commit()
    assert (stats.checked, stats.embedded) == (4, 4)
    assert await embeddings.to_embed(100, embedder.model) == [], "второй раз не считаем"

    search = SmartSearchUseCase(listings, embedder)
    page = await search.execute(
        ListingSearchFilters(query="нужен балкон", price_max=Decimal(2000)), page_size=10
    )
    assert [item.source_id for item in page.items][:1] == ["2"]
    assert "4" not in [item.source_id for item in page.items], "фильтр цены работает"
    assert page.total == 3

    sea = await search.execute(ListingSearchFilters(query="рядом море"), page_size=1)
    assert [item.source_id for item in sea.items] == ["3"]
    batumi_only = await search.execute(
        ListingSearchFilters(query="метро", city="batumi"), page_size=10
    )
    assert [item.source_id for item in batumi_only.items] == ["3"]


async def test_one_embedding_per_listing(session: AsyncSession) -> None:
    listing = await ListingsRepository(session).create_or_update_from_raw(flat("5", "Кот"))
    await session.commit()
    embeddings = EmbeddingsRepository(session)
    await embeddings.save_many([(listing.id, [0.1] * 1536)], "m")
    await embeddings.save_many([(listing.id, [0.2] * 1536)], "m")
    await session.commit()
    count = await session.scalar(select(func.count()).select_from(Embedding))
    assert count == 1
