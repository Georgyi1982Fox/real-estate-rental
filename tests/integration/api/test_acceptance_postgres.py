"""Акт приёмки квартиры (TASK-102) на настоящем PostgreSQL."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.acceptance import ITEMS
from bina.application.localization import script_of
from bina.application.ports.scraper import RawListing
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


def headers(language: str) -> dict[str, str]:
    return {
        "X-Telegram-Init-Data": sign_init_data(
            BOT_TOKEN, {"id": 779, "first_name": "Anna", "language_code": language}
        )
    }


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str, bytes, str]] = []

    async def __call__(self, chat_id: int, filename: str, content: bytes, caption: str) -> None:
        self.sent.append((chat_id, filename, content, caption))


@pytest.fixture
def sender() -> FakeSender:
    return FakeSender()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession], sender: FakeSender
) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    app.state.document_sender = sender
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def make_premium(session: AsyncSession) -> None:
    await session.execute(
        update(User)
        .where(User.telegram_id == 779)
        .values(
            subscription_tier=SubscriptionTier.NOMAD,
            subscription_expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await session.commit()


BODY = {
    "landlord_name": "Giorgi Beridze",
    "tenant_name": "Anna Smith",
    "handover_date": "2026-11-01",
    "items": [
        {"code": "entrance_door", "status": "ok"},
        {"code": "wardrobe", "status": "defect", "comment": "  Scratch  on the door "},
    ],
    "keys": 2,
    "electricity": "12345",
}


@pytest.mark.parametrize("language", ["ka", "ru", "en"])
async def test_checklist_in_user_language(client: AsyncClient, language: str) -> None:
    answer = await client.get("/api/documents/acceptance/checklist", headers=headers(language))
    assert answer.status_code == 200
    checklist = answer.json()
    titles = [section["title"] for section in checklist["sections"]]
    titles += [item["title"] for section in checklist["sections"] for item in section["items"]]
    titles += [item["title"] for item in checklist["statuses"]]
    assert all(script_of(title) == language for title in titles)
    codes = [item["code"] for section in checklist["sections"] for item in section["items"]]
    assert codes == list(ITEMS)
    assert [item["code"] for item in checklist["statuses"]] == ["ok", "defect", "missing"]


async def test_acceptance(client: AsyncClient, session: AsyncSession, sender: FakeSender) -> None:
    url = "/api/documents/acceptance"
    body = {**BODY, "address": "Paliashvili 1"}

    free = await client.post(url, json=body, headers=headers("ru"))
    assert free.status_code == 402
    await make_premium(session)

    no_address = await client.post(url, json=BODY, headers=headers("ru"))
    assert no_address.status_code == 422

    answer = await client.post(url, json=body, headers=headers("ru"))
    assert answer.status_code == 200
    assert answer.json() == {"sent": True, "filename": "bina-acceptance-2026-11-01.pdf"}
    chat_id, _, content, caption = sender.sent[0]
    assert chat_id == 779
    assert content.startswith(b"%PDF")
    assert caption.startswith("Акт приёмки квартиры (грузинский + русский)")

    file = await client.post(
        url, json={**body, "delivery": "file", "second_language": "en"}, headers=headers("ru")
    )
    assert file.headers["content-type"] == "application/pdf"
    assert len(sender.sent) == 1

    for bad in (
        {**body, "items": [{"code": "piano", "status": "ok"}]},
        {**body, "items": [{"code": "tv", "status": "broken"}]},
        {**body, "items": [{"code": "tv", "status": "ok"}, {"code": "tv", "status": "ok"}]},
        {**body, "items": []},
    ):
        assert (await client.post(url, json=bad, headers=headers("ru"))).status_code == 422


async def test_address_from_listing(
    client: AsyncClient, session: AsyncSession, sender: FakeSender
) -> None:
    listing = await ListingsRepository(session).create_or_update_from_raw(
        RawListing(
            source_id="a1",
            source_name="ss",
            title="Квартира",
            description="",
            price=1000,
            currency="USD",
            rooms=2,
            area=55,
            district="Ваке",
            url="https://ss.example/a1",
            address="Abashidze 5",
        )
    )
    await session.commit()
    await client.get("/api/documents/acceptance/checklist", headers=headers("en"))
    await make_premium(session)
    answer = await client.post(
        "/api/documents/acceptance",
        json={**BODY, "listing_id": str(listing.id)},
        headers=headers("en"),
    )
    assert answer.status_code == 200
    assert sender.sent[-1][3].startswith("Apartment handover report (Georgian + English)")

    missing = await client.post(
        "/api/documents/acceptance",
        json={**BODY, "listing_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers("en"),
    )
    assert missing.status_code == 404
