from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from bina.infrastructure.api.settings import ApiSettings
from tests.support.fakes import Store
from tests.support.telegram import sign_init_data

from .conftest import BOT_TOKEN, TELEGRAM_USER


@pytest.fixture
def listings(store: Store) -> list[str]:
    district = store.add_district("Ваке")
    return [str(store.add_listing(district, title_ru=f"Квартира {n}").id) for n in range(3)]


async def test_full_flow(
    client: AsyncClient,
    store: Store,
    listings: list[str],
    auth: dict[str, str],
    sessions: list[AsyncMock],
) -> None:
    for listing_id in (listings[0], listings[1], listings[0]):
        response = await client.post(
            "/api/favorites", json={"listing_id": listing_id}, headers=auth
        )
        assert response.status_code == 201
        assert response.json() == {"listing_id": listing_id, "is_favorite": True}
    assert sessions[-1].commit.await_count >= 1

    body = (await client.get("/api/favorites", headers=auth)).json()
    assert (body["total"], body["page"], body["pages"]) == (2, 1, 1)
    assert [item["id"] for item in body["items"]] == [listings[1], listings[0]]

    for _ in range(2):  # повторное удаление тоже 204
        response = await client.delete(f"/api/favorites/{listings[0]}", headers=auth)
        assert response.status_code == 204
    body = (await client.get("/api/favorites", headers=auth)).json()
    assert [item["id"] for item in body["items"]] == [listings[1]]

    user = store.users[555]
    assert user.language == "en", "пользователь зарегистрирован по данным Telegram"


async def test_favorites_are_per_user(
    client: AsyncClient,
    listings: list[str],
    auth: dict[str, str],
) -> None:
    await client.post("/api/favorites", json={"listing_id": listings[0]}, headers=auth)
    other = {"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, {**TELEGRAM_USER, "id": 777})}

    body = (await client.get("/api/favorites", headers=other)).json()

    assert body["total"] == 0


async def test_add_unknown_listing(client: AsyncClient, auth: dict[str, str]) -> None:
    response = await client.post("/api/favorites", json={"listing_id": str(uuid4())}, headers=auth)
    assert response.status_code == 404


async def test_add_requires_uuid(client: AsyncClient, auth: dict[str, str]) -> None:
    response = await client.post("/api/favorites", json={"listing_id": 1}, headers=auth)
    assert response.status_code == 422


async def test_matching_user_id_is_accepted(
    client: AsyncClient, listings: list[str], auth: dict[str, str]
) -> None:
    response = await client.get("/api/favorites", params={"user_id": 555}, headers=auth)
    assert response.status_code == 200


# --------------------------------------------------------------------------- auth


@pytest.mark.parametrize(
    ("headers", "params", "status"),
    [
        ({}, {}, 401),
        ({}, {"user_id": 555}, 401),
        ({"X-Telegram-Init-Data": "garbage"}, {}, 401),
        ({"X-Telegram-Init-Data": sign_init_data("999:OTHER", TELEGRAM_USER)}, {}, 401),
        ({"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, None)}, {}, 401),
        (
            {
                "X-Telegram-Init-Data": sign_init_data(
                    BOT_TOKEN, TELEGRAM_USER, datetime.now(UTC) - timedelta(days=2)
                )
            },
            {},
            401,
        ),
        ({"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, TELEGRAM_USER)}, {"user_id": 777}, 403),
    ],
    ids=["no-auth", "user-id-only", "garbage", "wrong-token", "no-user", "expired", "mismatch"],
)
async def test_auth_errors(
    client: AsyncClient,
    store: Store,
    headers: dict[str, str],
    params: dict[str, str | int],
    status: int,
) -> None:
    response = await client.get("/api/favorites", headers=headers, params=params)

    assert response.status_code == status
    assert store.users == {}


async def test_tampered_init_data_is_rejected(client: AsyncClient, auth: dict[str, str]) -> None:
    tampered = auth["X-Telegram-Init-Data"].replace("%22id%22%3A555", "%22id%22%3A777")
    assert tampered != auth["X-Telegram-Init-Data"]

    response = await client.get("/api/favorites", headers={"X-Telegram-Init-Data": tampered})

    assert response.status_code == 401


@pytest.mark.parametrize("settings", [ApiSettings(bot_token=None)])
async def test_missing_bot_token_is_server_error(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.get("/api/favorites", headers=auth)
    assert response.status_code == 503


@pytest.mark.parametrize("settings", [ApiSettings(bot_token=None, allow_insecure_user_id=True)])
async def test_insecure_user_id_mode(
    client: AsyncClient, store: Store, listings: list[str]
) -> None:
    response = await client.post(
        "/api/favorites", params={"user_id": 42}, json={"listing_id": listings[0]}
    )

    assert response.status_code == 201
    assert 42 in store.users
