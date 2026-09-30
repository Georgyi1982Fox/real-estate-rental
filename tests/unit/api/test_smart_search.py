"""``GET /api/listings?sort=smart``: умный поиск по смыслу (TASK-012)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from tests.support.embeddings import FakeEmbedder
from tests.support.fakes import Store


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
async def smart_client(
    store: Store, settings: ApiSettings, embedder: FakeEmbedder
) -> AsyncIterator[AsyncClient]:
    @asynccontextmanager
    async def session_factory() -> AsyncIterator[AsyncMock]:
        yield AsyncMock(spec=AsyncSession)

    app = create_app(settings, cast(async_sessionmaker[AsyncSession], session_factory))
    app.state.embedder = embedder
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
def seeded(store: Store) -> Store:
    vake = store.add_district("Ваке")
    store.add_listing(vake, price=900, title_ru="Квартира у метро")
    store.add_listing(vake, price=1000, title_ru="Квартира с балконом")
    store.add_listing(vake, price=3000, title_ru="Дорогая квартира с балконом")
    store.add_listing(vake, price=1100, title_ru="Квартира в центре")
    return store


async def test_ranked_by_meaning(smart_client: AsyncClient, seeded: Store) -> None:
    response = await smart_client.get(
        "/api/listings", params={"q": "балкон", "sort": "smart", "max_price": 2000}
    )
    assert response.status_code == 200
    titles = [item["title"]["ru"] for item in response.json()["items"]]
    assert titles[0] == "Квартира с балконом", "совпадение по смыслу — первым"
    assert "Дорогая квартира с балконом" not in titles, "остальные фильтры работают"
    assert "Квартира у метро" in titles, "совпадение слов не требуется"


async def test_service_down_falls_back_to_text_search(
    smart_client: AsyncClient, seeded: Store, embedder: FakeEmbedder
) -> None:
    embedder.fail = True
    response = await smart_client.get("/api/listings", params={"q": "балкон", "sort": "smart"})
    assert response.status_code == 200


async def test_smart_without_query_is_newest(
    smart_client: AsyncClient, seeded: Store, embedder: FakeEmbedder
) -> None:
    response = await smart_client.get("/api/listings", params={"sort": "smart"})
    assert response.status_code == 200
    assert response.json()["total"] == 4
    assert embedder.calls == []
