"""Полнотекстовый поиск на настоящем PostgreSQL (TASK-022)."""

from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import District, Listing


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token="1:T"), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
async def listings(session: AsyncSession) -> dict[str, Listing]:
    district = District(
        name_ru="Ваке",
        name_ka="ვაკე",
        name_en="Vake",
        avg_price_per_m2=Decimal(20),
        safety_score=9,
        is_deleted=False,
    )
    session.add(district)
    await session.flush()
    data = {
        "vake": ("Сдается 2-комнатная квартира в ваке", "Рядом парк Ваке, метро 5 минут", 1500),
        "saburtalo": ("Аренда 3-комнатная Квартира. Сабуртало", "Новый ремонт, балкон", 2000),
        "gldani": ("Сдается квартира в глдани", "Описание про ваке нет", 900),
    }
    items: dict[str, Listing] = {}
    for key, (title, description, price) in data.items():
        items[key] = Listing(
            source_id=key,
            source_name="ss",
            title_ru=title,
            title_ka="",
            description_ru=description,
            description_ka="",
            price=Decimal(price),
            district_id=district.id,
            rooms=2,
            area=Decimal(60),
        )
    session.add_all(items.values())
    await session.commit()
    return items


async def ids(client: AsyncClient, **params: str) -> list[str]:
    body = (await client.get("/api/listings", params=params)).json()
    return [item["title"]["ru"] for item in body["items"]]


async def test_russian_word_forms_and_prefix(
    client: AsyncClient, listings: dict[str, Listing]
) -> None:
    # «комнаты» находит «2-комнатная» (словоформы), «сабурт» — «Сабуртало» (начало слова)
    assert await ids(client, q="комнаты ваке") == ["Сдается 2-комнатная квартира в ваке"]
    assert await ids(client, q="сабурт") == ["Аренда 3-комнатная Квартира. Сабуртало"]
    assert await ids(client, q="балкон") == ["Аренда 3-комнатная Квартира. Сабуртало"]
    assert await ids(client, q="метро парк") == ["Сдается 2-комнатная квартира в ваке"]
    assert await ids(client, q="бассейн") == []


async def test_relevance_title_before_description(
    client: AsyncClient, listings: dict[str, Listing]
) -> None:
    # «ваке» в заголовке (вес A) выше, чем только в описании (вес B)
    result = await ids(client, q="ваке")
    assert result == ["Сдается 2-комнатная квартира в ваке", "Сдается квартира в глдани"]
    # Явная сортировка важнее релевантности
    by_price = await ids(client, q="ваке", sort="price_asc")
    assert by_price == ["Сдается квартира в глдани", "Сдается 2-комнатная квартира в ваке"]


async def test_search_with_filters_and_translations(
    client: AsyncClient, session: AsyncSession, listings: dict[str, Listing]
) -> None:
    assert await ids(client, q="квартира", max_price="1000") == ["Сдается квартира в глдани"]

    # Перевод (TASK-010) сразу участвует в поиске: вычисляемый столбец обновляется сам
    await session.execute(
        update(Listing)
        .where(Listing.source_id == "saburtalo")
        .values(
            title_en="3-room apartment for rent in Saburtalo", title_ka="ქირავდება ბინა საბურთალოზე"
        )
    )
    await session.commit()
    assert await ids(client, q="apartments rent") == ["Аренда 3-комнатная Квартира. Сабуртало"]
    assert await ids(client, q="საბურთალო") == ["Аренда 3-комнатная Квартира. Сабуртало"]


async def test_special_characters_are_safe(
    client: AsyncClient, listings: dict[str, Listing]
) -> None:
    for query in ["ваке & | ! :*", "'); drop table bina_listings; --", "<>", "(ваке"]:
        response = await client.get("/api/listings", params={"q": query})
        assert response.status_code == 200, query
    assert await ids(client, q="(ваке") != []
    assert len(await ids(client, q="<>")) == 3  # без слов — как пустой поиск
