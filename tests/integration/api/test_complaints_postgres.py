"""Жалобы на объявления (TASK-106) на настоящем PostgreSQL."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.localization import script_of
from bina.application.ports.scraper import RawListing
from bina.infrastructure.api.routes import complaints as complaint_routes
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


def headers(user_id: int, language: str = "ru") -> dict[str, str]:
    return {
        "X-Telegram-Init-Data": sign_init_data(
            BOT_TOKEN, {"id": user_id, "first_name": "Anna", "language_code": language}
        )
    }


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def add(session: AsyncSession, source_id: str) -> Listing:
    listing = await ListingsRepository(session).create_or_update_from_raw(
        RawListing(
            source_id=source_id,
            source_name="ss",
            title="Квартира",
            description="",
            price=1000,
            currency="GEL",
            rooms=2,
            area=50,
            district="Ваке",
            url=f"https://ss.example/{source_id}",
        )
    )
    await session.commit()
    return listing


async def search_ids(client: AsyncClient) -> set[str]:
    answer = await client.get("/api/listings", headers=headers(900))
    return {item["id"] for item in answer.json()["items"]}


@pytest.mark.parametrize("language", ["ka", "ru", "en"])
async def test_reasons(client: AsyncClient, language: str) -> None:
    user = {"ka": 901, "ru": 902, "en": 903}[language]
    reasons = (await client.get("/api/complaints/reasons", headers=headers(user, language))).json()
    assert reasons[0]["code"] == "fraud"
    assert all(script_of(reason["title"]) == language for reason in reasons)


async def test_three_people_hide_listing(client: AsyncClient, session: AsyncSession) -> None:
    listing = await add(session, "scam")
    other = await add(session, "fine")
    url = f"/api/listings/{listing.id}/complaints"
    assert await search_ids(client) == {str(listing.id), str(other.id)}

    first = await client.post(url, json={"reason": "fraud"}, headers=headers(911, "en"))
    assert first.status_code == 200
    assert first.json() == {"accepted": True, "message": "Thank you! We will check the listing."}
    # Тот же человек ещё раз — всё равно одна жалоба
    again = {"reason": "prepayment", "comment": "  wants  money "}
    await client.post(url, json=again, headers=headers(911, "en"))
    await client.post(url, json={"reason": "wrong_photos"}, headers=headers(912))
    assert str(listing.id) in await search_ids(client), "двух жалоб мало"

    await client.post(url, json={"reason": "fraud"}, headers=headers(913))
    assert await search_ids(client) == {str(other.id)}
    # По прямой ссылке (избранное) объявление открывается
    assert (await client.get(f"/api/listings/{listing.id}")).status_code == 200


async def test_complaint_errors(
    client: AsyncClient, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    listing = await add(session, "x")
    url = f"/api/listings/{listing.id}/complaints"
    assert (
        await client.post(url, json={"reason": "ugly"}, headers=headers(921))
    ).status_code == 422
    long = {"reason": "other", "comment": "a" * 501}
    assert (await client.post(url, json=long, headers=headers(921))).status_code == 422
    missing = "/api/listings/00000000-0000-0000-0000-000000000000/complaints"
    assert (
        await client.post(missing, json={"reason": "fraud"}, headers=headers(921))
    ).status_code == 404

    monkeypatch.setattr(complaint_routes, "DAILY_LIMIT", 1)
    second = await add(session, "y")
    assert (
        await client.post(url, json={"reason": "fraud"}, headers=headers(921))
    ).status_code == 200
    limited = await client.post(
        f"/api/listings/{second.id}/complaints", json={"reason": "fraud"}, headers=headers(921)
    )
    assert limited.status_code == 429
