"""AI-помощник и «похожие дешевле» (TASK-095) на настоящем PostgreSQL."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.assistant import IAssistant, ListingBrief, OwnerMessage
from bina.application.ports.scraper import RawListing
from bina.infrastructure.api.routes import assistant as assistant_routes
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
HEADERS = {
    "X-Telegram-Init-Data": sign_init_data(
        BOT_TOKEN, {"id": 777, "first_name": "Nino", "language_code": "ru"}
    )
}


class FakeAssistant(IAssistant):
    def __init__(self) -> None:
        self.briefs: list[tuple[ListingBrief, str, str]] = []

    async def message_owner(self, listing: ListingBrief, language: str, note: str) -> OwnerMessage:
        self.briefs.append((listing, language, note))
        return OwnerMessage(text_ka="გამარჯობა!", translation="Здравствуйте!")

    async def viewing_questions(self, listing: ListingBrief, language: str, note: str) -> list[str]:
        self.briefs.append((listing, language, note))
        return ["Какое отопление зимой?", "Что входит в цену?"]


def raw(source_id: str, price: float, rooms: int = 2, area: float = 60.0) -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="ss",
        title=f"Квартира {source_id}",
        description="Описание квартиры",
        price=price,
        currency="GEL",
        rooms=rooms,
        area=area,
        district="Ваке",
        url=f"https://ss.example/{source_id}",
    )


@pytest.fixture
def fake() -> FakeAssistant:
    return FakeAssistant()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession], fake: FakeAssistant
) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    app.state.assistant = fake
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def make_premium(session: AsyncSession) -> None:
    await session.execute(
        update(User)
        .where(User.telegram_id == 777)
        .values(
            subscription_tier=SubscriptionTier.NOMAD,
            subscription_expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await session.commit()


async def test_assistant(
    client: AsyncClient,
    session: AsyncSession,
    fake: FakeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listing = await ListingsRepository(session).create_or_update_from_raw(raw("a", 1500))
    await session.commit()
    url = f"/api/listings/{listing.id}/assistant"
    body = {"action": "message_owner", "note": "  двое,  с кошкой "}

    free = await client.post(url, json=body, headers=HEADERS)
    assert free.status_code == 402
    assert fake.briefs == []

    await make_premium(session)
    monkeypatch.setattr(assistant_routes, "DAILY_LIMIT", 2)
    answer = (await client.post(url, json=body, headers=HEADERS)).json()
    assert answer == {
        "action": "message_owner",
        "text_ka": "გამარჯობა!",
        "translation": "Здравствуйте!",
        "questions": [],
        "remaining_today": 1,
    }
    brief, language, note = fake.briefs[0]
    assert (brief.price, brief.rooms, brief.district, language, note) == (
        "1500 GEL",
        2,
        "Vake",
        "ru",
        "двое, с кошкой",
    )

    questions = (
        await client.post(url, json={"action": "viewing_questions"}, headers=HEADERS)
    ).json()
    assert questions["questions"] == ["Какое отопление зимой?", "Что входит в цену?"]
    assert questions["remaining_today"] == 0

    limited = await client.post(url, json={"action": "viewing_questions"}, headers=HEADERS)
    assert limited.status_code == 429
    assert len(fake.briefs) == 2, "после лимита AI не вызывается"

    bad = await client.post(url, json={"action": "write_poem"}, headers=HEADERS)
    assert bad.status_code == 422


async def test_cheaper_similar(client: AsyncClient, session: AsyncSession) -> None:
    repository = ListingsRepository(session)
    target = await repository.create_or_update_from_raw(raw("t", 1500))
    for source_id, price, rooms, area in (
        ("c1", 1200, 2, 58),
        ("c2", 1000, 2, 65),
        ("pricier", 1700, 2, 60),
        ("bigger", 900, 2, 90),  # площадь больше чем на 20%
        ("other_rooms", 900, 3, 60),
    ):
        await repository.create_or_update_from_raw(raw(source_id, price, rooms, area))
    await session.commit()
    url = f"/api/listings/{target.id}/cheaper"

    assert (await client.get(url, headers=HEADERS)).status_code == 402
    await make_premium(session)
    items = (await client.get(url, headers=HEADERS)).json()["items"]
    assert [item["source_url"] for item in items] == [
        "https://ss.example/c2",
        "https://ss.example/c1",
    ]
