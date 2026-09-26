from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.support.fakes import Store


@pytest.fixture
def seeded(store: Store) -> Store:
    vake = store.add_district("Ваке", name_en="Vake", name_ka="ვაკე")
    saburtalo = store.add_district("Сабуртало")
    for price, rooms in [(900, 1), (1000, 2), (1200, 2), (1400, 3), (1600, 4), (2500, 5)]:
        store.add_listing(vake, price=price, rooms=rooms, title_ru=f"Ваке {price}")
    store.add_listing(saburtalo, price=1100, title_ru="Сабуртало 1100")
    store.add_listing(vake, price=1100, title_ru="Удалённое", is_deleted=True)
    return store


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.json() == {"status": "ok"}


async def test_list_is_paginated_newest_first(client: AsyncClient, seeded: Store) -> None:
    response = await client.get("/api/listings", params={"page": 2, "per_page": 3})

    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["page"], body["pages"]) == (7, 2, 3)
    titles = [item["title"]["ru"] for item in body["items"]]
    assert titles == ["Ваке 1400", "Ваке 1200", "Ваке 1000"]


async def test_listing_shape(client: AsyncClient, seeded: Store) -> None:
    listing = seeded.listings[0]

    response = await client.get(f"/api/listings/{listing.id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(listing.id),
        "title": {"ka": "ბინა", "ru": "Ваке 900"},
        "description": {},
        "price": 900.0,
        "currency": "GEL",
        "rooms": 1,
        "area": 50.0,
        "district": str(listing.district_id),
        "is_verified": False,
        "images": [],
    }


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"min_price": "1000", "max_price": "1400"}, [1100, 1400, 1200, 1000]),
        ({"rooms": 2}, [1100, 1200, 1000]),
        ({"rooms": 4}, [2500, 1600]),
        (
            {"min_price": "", "max_price": "", "district": ""},
            [1100, 2500, 1600, 1400, 1200, 1000, 900],
        ),
    ],
)
async def test_filters(
    client: AsyncClient,
    seeded: Store,
    params: dict[str, str | int],
    expected: list[int],
) -> None:
    response = await client.get("/api/listings", params=params)

    assert response.status_code == 200
    assert [item["price"] for item in response.json()["items"]] == expected


async def test_district_filter(client: AsyncClient, seeded: Store) -> None:
    saburtalo = seeded.districts[1]

    response = await client.get("/api/listings", params={"district": str(saburtalo.id)})

    assert [item["title"]["ru"] for item in response.json()["items"]] == ["Сабуртало 1100"]


@pytest.mark.parametrize(
    "params",
    [
        {"district": "vake"},
        {"min_price": "abc"},
        {"min_price": "-1"},
        {"min_price": "5", "max_price": "1"},
        {"per_page": 51},
        {"page": 0},
        {"rooms": 0},
    ],
)
async def test_invalid_params(
    client: AsyncClient, seeded: Store, params: dict[str, str | int]
) -> None:
    response = await client.get("/api/listings", params=params)
    assert response.status_code == 422


@pytest.mark.parametrize("listing_id", ["1", "not-a-uuid", str(uuid4())])
async def test_unknown_listing(client: AsyncClient, seeded: Store, listing_id: str) -> None:
    response = await client.get(f"/api/listings/{listing_id}")
    assert response.status_code == 404


async def test_deleted_listing_is_hidden(client: AsyncClient, seeded: Store) -> None:
    deleted = seeded.listings[-1]
    assert (await client.get(f"/api/listings/{deleted.id}")).status_code == 404


async def test_similar(client: AsyncClient, seeded: Store) -> None:
    listing = next(item for item in seeded.listings if item.price == 1200)

    response = await client.get(f"/api/listings/{listing.id}/similar")

    prices = [item["price"] for item in response.json()["items"]]
    # тот же район, ±30% (840..1560), без самого объявления, удалённых и других районов
    assert prices == [1400, 1000, 900]


async def test_similar_of_unknown_listing(client: AsyncClient, seeded: Store) -> None:
    assert (await client.get(f"/api/listings/{uuid4()}/similar")).status_code == 404


async def test_districts(client: AsyncClient, seeded: Store) -> None:
    response = await client.get("/api/districts")

    assert response.json()["items"][0] == {
        "id": str(seeded.districts[0].id),
        "name": {"ka": "ვაკე", "ru": "Ваке", "en": "Vake"},
    }
