from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.support.fakes import Store


@pytest.fixture
def seeded(store: Store) -> Store:
    vake = store.add_district("Ваке", name_en="Vake", name_ka="ვაკე")
    saburtalo = store.add_district("Сабуртало")
    for price, rooms in [(900, 1), (1000, 2), (1200, 2), (1400, 3), (1600, 4), (2500, 5)]:
        store.add_listing(
            vake, price=price, rooms=rooms, title_ru=f"Ваке {price}", images=[f"/img/{price}.jpg"]
        )
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
        "rent_period": "monthly",
        "rooms": 1,
        "area": 50.0,
        "district": str(listing.district_id),
        "is_verified": False,
        "repair_level": None,
        "is_premium_listing": False,
        "agency": None,
        "is_promoted": False,
        "images": ["/img/900.jpg"],
        "has_phone": False,
        "source_url": None,
        "source": "test",
        "views": 1,
        "also_on": [],
        "owner_name": None,
        "fraud_level": "none",
        "fraud_reasons": [],
        "floor": None,
        "total_floors": None,
        "bedrooms": None,
        "bathrooms": None,
        "condition": None,
        "features": [],
        "owner_type": None,
        "address": {},
        "owner": None,
        "latitude": None,
        "longitude": None,
        # Даты с сайта нет — дата появления у нас
        "published_at": listing.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": None,
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


async def test_similar_falls_back_to_district_then_price(client: AsyncClient, store: Store) -> None:
    vake = store.add_district("Ваке")
    other = store.add_district("Сабуртало")
    store.add_listing(other, price=5000, title_ru="Чужой дорогой")  # не подходит ни по чему
    store.add_listing(other, price=1100, title_ru="Чужой по цене")
    store.add_listing(vake, price=3000, title_ru="Ваке дорогой")
    target = store.add_listing(vake, price=1000, title_ru="Цель")

    response = await client.get(f"/api/listings/{target.id}/similar")

    # тот же район ±30% — нет; тот же район — «Ваке дорогой»; ±30% других районов — «Чужой по цене»
    titles = [item["title"]["ru"] for item in response.json()["items"]]
    assert titles == ["Ваке дорогой", "Чужой по цене"]


async def test_similar_of_unknown_listing(client: AsyncClient, seeded: Store) -> None:
    assert (await client.get(f"/api/listings/{uuid4()}/similar")).status_code == 404


async def test_districts(client: AsyncClient, seeded: Store) -> None:
    response = await client.get("/api/districts")

    assert response.json()["items"][0] == {
        "id": str(seeded.districts[0].id),
        "name": {"ka": "ვაკე", "ru": "Ваке", "en": "Vake"},
        "city": "tbilisi",
    }


async def test_city_filter(client: AsyncClient, seeded: Store) -> None:
    """TASK-079: районы и объявления одного города; список городов."""
    batumi = seeded.add_district("Старый Батуми", "Old Batumi", "ძველი ბათუმი", city="batumi")
    seeded.add_listing(batumi, price=900)

    districts = (await client.get("/api/districts", params={"city": "batumi"})).json()["items"]
    assert [item["id"] for item in districts] == [str(batumi.id)]
    listings = (await client.get("/api/listings", params={"city": "batumi"})).json()["items"]
    assert [item["district"] for item in listings] == [str(batumi.id)]
    tbilisi = (await client.get("/api/listings", params={"city": "tbilisi"})).json()["items"]
    assert tbilisi and all(item["district"] != str(batumi.id) for item in tbilisi)
    # Кутаиси — известный город (TASK-079), просто пока без объявлений
    empty = await client.get("/api/listings", params={"city": "kutaisi"})
    assert empty.status_code == 200 and empty.json()["items"] == []
    assert (await client.get("/api/listings", params={"city": "paris"})).status_code == 422

    cities = (await client.get("/api/cities")).json()["items"]
    assert [city["code"] for city in cities] == ["tbilisi", "batumi"]
    assert cities[1]["name"] == {"ka": "ბათუმი", "ru": "Батуми", "en": "Batumi"}


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("newest", [4, 3, 2, 1]),
        ("price_asc", [1, 2, 3, 4]),
        ("price_desc", [4, 3, 2, 1]),
        ("area_desc", [3, 1, 4, 2]),
        ("price_per_m2_asc", [1, 3, 2, 4]),
    ],
)
async def test_sort(client: AsyncClient, store: Store, sort: str, expected: list[int]) -> None:
    district = store.add_district("Ваке")
    # (цена, площадь): за м² — 10, 40, 20, 50
    for number, (price, area) in enumerate([(1000, 100), (2000, 50), (3000, 150), (4000, 80)], 1):
        store.add_listing(district, price=price, title_ru=f"№{number}", area=area)

    body = (await client.get("/api/listings", params={"sort": sort})).json()

    assert [int(item["title"]["ru"][1:]) for item in body["items"]] == expected


async def test_area_filter_and_bad_sort(client: AsyncClient, store: Store) -> None:
    district = store.add_district("Ваке")
    for area in (40, 60, 90):
        store.add_listing(district, title_ru=f"{area}", area=area)

    body = (await client.get("/api/listings", params={"min_area": "50", "max_area": "90"})).json()
    assert sorted(item["title"]["ru"] for item in body["items"]) == ["60", "90"]

    assert (await client.get("/api/listings", params={"sort": "cheapest"})).status_code == 422
    assert (
        await client.get("/api/listings", params={"min_area": "90", "max_area": "50"})
    ).status_code == 422
    assert (await client.get("/api/listings", params={"min_area": "-1"})).status_code == 422


async def test_text_search(client: AsyncClient, store: Store) -> None:
    district = store.add_district("Ваке")
    store.add_listing(district, title_ru="Сдается квартира в Ваке")
    store.add_listing(district, title_ru="Квартира в Сабуртало")

    async def titles(**params: str) -> list[str]:
        body = (await client.get("/api/listings", params=params)).json()
        return [item["title"]["ru"] for item in body["items"]]

    assert await titles(q="ваке") == ["Сдается квартира в Ваке"]
    assert await titles(q="  <b>сабурт</b> ") == ["Квартира в Сабуртало"]
    assert len(await titles(q="")) == 2
    assert len(await titles(q="!!!")) == 2  # без слов — как пустой поиск
    long = await client.get("/api/listings", params={"q": "x" * 101})
    assert long.status_code == 422


async def test_daily_rent_only_on_request(client: AsyncClient, store: Store) -> None:
    """TASK-092: по умолчанию — помесячная аренда; посуточная — с rent_period=daily."""
    vake = store.add_district("Ваке")
    store.add_listing(vake, price=1500, title_ru="Помесячно")
    store.add_listing(vake, price=60, title_ru="Посуточно", rent_period="daily")

    default = (await client.get("/api/listings")).json()
    daily = (await client.get("/api/listings", params={"rent_period": "daily"})).json()
    wrong = await client.get("/api/listings", params={"rent_period": "weekly"})

    assert [item["title"]["ru"] for item in default["items"]] == ["Помесячно"]
    assert [(item["title"]["ru"], item["rent_period"]) for item in daily["items"]] == [
        ("Посуточно", "daily")
    ]
    assert wrong.status_code in (400, 422)
