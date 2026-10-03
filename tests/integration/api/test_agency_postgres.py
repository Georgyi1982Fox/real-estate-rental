"""Кабинет агентства в API Mini App (TASK-100), на настоящем PostgreSQL."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from tests.integration.api.test_my_listings_postgres import BODY, BOT_TOKEN, headers, png

REALTOR = 801
TENANT = 802


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    monkeypatch.delenv("PREMIUM_FOR_ALL", raising=False)
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    app.state.bot_username = "bina_bot"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_realtor_cabinet_page_and_stats(client: AsyncClient) -> None:
    me = headers(REALTOR)
    assert (await client.get("/api/agency", headers=me)).status_code == 404

    created = await client.post(
        "/api/agency", json={"name": "  Batumi   Homes ", "phone": "+995 599 00 11 22"}, headers=me
    )
    assert created.status_code == 201, created.text
    agency: dict[str, Any] = created.json()
    assert (agency["name"], agency["phone"], agency["limit"]) == (
        "Batumi Homes",
        "+995599001122",
        10,
    )
    assert [plan["listings"] for plan in agency["plans"]] == [20, 30, 40]
    assert (await client.post("/api/agency", json={"name": "Again"}, headers=me)).status_code == 409

    patched = await client.patch("/api/agency", json={"description": "Квартиры у моря"}, headers=me)
    assert patched.json()["description"] == "Квартиры у моря"
    logo = await client.post(
        "/api/agency/logo", content=png(), headers={**me, "Content-Type": "image/png"}
    )
    assert logo.status_code == 200, logo.text
    assert "/agency-" in logo.json()["logo_url"]

    # Объявление агентства: «Кто сдаёт — агентство», лимит 10 (не 5)
    listing = (await client.post("/api/my/listings", json=BODY, headers=me)).json()
    assert (await client.get("/api/my/listings", headers=me)).json()["limit"] == 10

    tenant = headers(TENANT, username="tenant")
    detail = (await client.get(f"/api/listings/{listing['id']}", headers=tenant)).json()
    assert detail["agency"]["name"] == "Batumi Homes"
    assert detail["owner_type"] == "agent"
    await client.get(f"/api/listings/{listing['id']}", headers=tenant)
    await client.post(f"/api/listings/{listing['id']}/contact", headers=tenant)

    cabinet = (await client.get("/api/agency", headers=me)).json()
    [stats] = cabinet["listings"]
    assert (stats["views"], stats["contacts"], stats["active"]) == (2, 1, True)
    assert cabinet["active"] == 1

    page = await client.get(f"/api/agencies/{agency['id']}")
    assert page.status_code == 200
    body = page.json()
    assert (body["name"], body["description"]) == ("Batumi Homes", "Квартиры у моря")
    assert [item["id"] for item in body["listings"]] == [listing["id"]]


async def test_owner_without_agency_keeps_limit_five(client: AsyncClient) -> None:
    assert (await client.get("/api/my/listings", headers=headers(TENANT))).json()["limit"] == 5
