"""Калькулятор полной стоимости (TASK-103) на настоящем PostgreSQL."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.localization import script_of
from bina.application.ports.scraper import RawListing
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


def headers(language: str) -> dict[str, str]:
    return {
        "X-Telegram-Init-Data": sign_init_data(
            BOT_TOKEN, {"id": 780, "first_name": "Anna", "language_code": language}
        )
    }


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def listing_id(session: AsyncSession) -> str:
    listing = await ListingsRepository(session).create_or_update_from_raw(
        RawListing(
            source_id="k1",
            source_name="ss",
            title="Квартира",
            description="",
            price=700,
            currency="USD",
            rooms=2,
            area=60,
            district="Ваке",
            url="https://ss.example/k1",
        )
    )
    await session.commit()
    return str(listing.id)


async def test_costs(client: AsyncClient, session: AsyncSession) -> None:
    url = f"/api/listings/{await listing_id(session)}/costs"
    answer = await client.get(
        url, params={"start": "2026-11", "agency_fee_percent": 50}, headers=headers("en")
    )
    assert answer.status_code == 200
    costs = answer.json()
    assert (costs["currency"], costs["rent"], costs["rent_currency"]) == ("GEL", 1890, "USD")
    assert (costs["deposit"], costs["agency_fee"], costs["period_months"]) == (1890, 945, 12)
    first = costs["first_month"]
    assert first["total"] == 1890 + 1890 + 945 + first["utilities"]
    assert costs["monthly"][0]["month"] == "2026-11"
    assert costs["monthly"][2]["month"] == "2027-01"
    winter, summer = costs["monthly"][2], costs["monthly"][7]
    assert winter["items"]["gas"] > summer["items"]["gas"]
    assert costs["heating"] == "gas"
    assert [item["title"] for item in costs["items"]][:2] == ["Electricity", "Gas"]
    assert script_of(costs["note"]) == "en"

    included = (
        await client.get(
            url, params={"utilities_included": "true", "months": 6}, headers=headers("en")
        )
    ).json()
    assert included["period_total"] == 1890 * 6
    assert included["average_utilities"] == 0


@pytest.mark.parametrize("language", ["ka", "ru"])
async def test_costs_in_user_language(
    client: AsyncClient, session: AsyncSession, language: str
) -> None:
    url = f"/api/listings/{await listing_id(session)}/costs"
    costs = (await client.get(url, headers=headers(language))).json()
    assert all(script_of(item["title"]) == language for item in costs["items"])
    assert script_of(costs["note"]) == language


async def test_costs_errors(client: AsyncClient, session: AsyncSession) -> None:
    url = f"/api/listings/{await listing_id(session)}/costs"
    for params in ({"start": "november"}, {"people": 0}, {"months": 36}, {"deposit_months": 5}):
        assert (await client.get(url, params=params, headers=headers("en"))).status_code == 422
    missing = "/api/listings/00000000-0000-0000-0000-000000000000/costs"
    assert (await client.get(missing, headers=headers("en"))).status_code == 404
