"""Телефон, «Написать» и профиль текущего пользователя."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import AsyncClient

from bina.infrastructure.db.models import ListingStatus
from tests.support.fakes import Store

URL = "https://www.myhome.ge/ru/nedvizhimost/sdaetsia-kvartira-26173256/"


async def test_listing_exposes_contact_fields(client: AsyncClient, store: Store) -> None:
    district = store.add_district("Ваке")
    with_contacts = store.add_listing(district, url=URL, phone="+995555123456", owner_name="Нино")
    without = store.add_listing(district)

    body = (await client.get(f"/api/listings/{with_contacts.id}")).json()
    assert (body["has_phone"], body["source_url"], body["owner_name"]) == (True, URL, "Нино")
    body = (await client.get(f"/api/listings/{without.id}")).json()
    assert (body["has_phone"], body["source_url"], body["owner_name"]) == (False, None, None)


async def test_phone(client: AsyncClient, store: Store) -> None:
    district = store.add_district("Ваке")
    listing = store.add_listing(district, phone="+995555123456")

    response = await client.get(f"/api/listings/{listing.id}/phone")
    assert response.status_code == 200
    assert response.json() == {"phone": "+995555123456"}


async def test_owner_phone_needs_login(
    client: AsyncClient, store: Store, auth: dict[str, str]
) -> None:
    """Номера хозяев, разместивших объявление у нас, скриптом без входа не собрать."""
    listing = store.add_listing(store.add_district("Ваке"), phone="+995555123456")
    listing.source_name = "owner"

    url = f"/api/listings/{listing.id}/phone"
    assert (await client.get(url)).status_code == 401
    assert (await client.get(url, headers=auth)).json() == {"phone": "+995555123456"}


async def test_no_contacts_for_hidden_or_rented(client: AsyncClient, store: Store) -> None:
    district = store.add_district("Ваке")
    hidden = store.add_listing(district, url=URL, phone="+995555123456")
    hidden.hidden_at = datetime.now(UTC)
    rented = store.add_listing(
        district, url=URL, phone="+995555123456", status=ListingStatus.ARCHIVED
    )

    for listing in (hidden, rented):
        assert (await client.get(f"/api/listings/{listing.id}/phone")).status_code == 404
        assert (await client.post(f"/api/listings/{listing.id}/contact")).status_code == 404
    # Само объявление по старой ссылке открывается
    assert (await client.get(f"/api/listings/{hidden.id}")).status_code == 200


async def test_phone_missing(client: AsyncClient, store: Store) -> None:
    listing = store.add_listing(store.add_district("Ваке"))

    assert (await client.get(f"/api/listings/{listing.id}/phone")).status_code == 404
    assert (await client.get(f"/api/listings/{uuid4()}/phone")).status_code == 404


async def test_contact_returns_source_url(client: AsyncClient, store: Store) -> None:
    district = store.add_district("Ваке")
    listing = store.add_listing(district, url=URL)

    response = await client.post(f"/api/listings/{listing.id}/contact")
    assert response.status_code == 200
    assert response.json() == {"url": URL}

    no_url = store.add_listing(district)
    assert (await client.post(f"/api/listings/{no_url.id}/contact")).status_code == 404


async def test_me_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/me")).status_code == 401


async def test_me(client: AsyncClient, store: Store, auth: dict[str, str]) -> None:
    district = store.add_district("Ваке")
    listing = store.add_listing(district)
    response = await client.post(
        "/api/favorites", json={"listing_id": str(listing.id)}, headers=auth
    )
    assert response.status_code == 201

    body = (await client.get("/api/me", headers=auth)).json()

    assert body["telegram_id"] == 555
    assert body["language"] == "en"
    assert body["subscription_tier"] == "free"
    assert body["subscription_expires_at"] is None
    assert body["balance"] == 0
    assert body["favorites_count"] == 1
    assert body["created_at"]


async def test_update_language(
    client: AsyncClient, store: Store, auth: dict[str, str], sessions: list[AsyncMock]
) -> None:
    response = await client.patch("/api/me", json={"language": "ka"}, headers=auth)

    assert response.status_code == 200
    assert response.json()["language"] == "ka"
    assert store.users[555].language == "ka"
    assert sessions[-1].commit.await_count >= 1
    assert (await client.get("/api/me", headers=auth)).json()["language"] == "ka"


async def test_update_language_rejects_unknown(client: AsyncClient, auth: dict[str, str]) -> None:
    response = await client.patch("/api/me", json={"language": "de"}, headers=auth)
    assert response.status_code == 422
