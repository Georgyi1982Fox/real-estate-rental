"""Договор аренды в PDF (TASK-101) на настоящем PostgreSQL."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
            BOT_TOKEN, {"id": 778, "first_name": "Anna", "language_code": language}
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
        .where(User.telegram_id == 778)
        .values(
            subscription_tier=SubscriptionTier.NOMAD,
            subscription_expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await session.commit()


BODY = {
    "landlord_name": "  Giorgi   Beridze ",
    "tenant_name": "Anna Smith",
    "start_date": "2026-11-01",
    "months": 12,
    "deposit": 1500,
    "payment_day": 5,
}


async def test_contract(client: AsyncClient, session: AsyncSession, sender: FakeSender) -> None:
    listing = await ListingsRepository(session).create_or_update_from_raw(
        RawListing(
            source_id="c1",
            source_name="ss",
            title="Квартира",
            description="",
            price=1500,
            currency="GEL",
            rooms=2,
            area=60,
            district="Ваке",
            url="https://ss.example/c1",
        )
    )
    await session.commit()
    url = f"/api/listings/{listing.id}/contract"

    free = await client.post(url, json={**BODY, "address": "Paliashvili 1"}, headers=headers("en"))
    assert free.status_code == 402
    await make_premium(session)

    # У объявления нет адреса — его нужно указать
    no_address = await client.post(url, json=BODY, headers=headers("en"))
    assert no_address.status_code == 422

    body = {**BODY, "address": "Paliashvili 1"}
    answer = await client.post(url, json=body, headers=headers("en"))
    assert answer.status_code == 200
    assert answer.json() == {"sent": True, "filename": "bina-contract-2026-11-01.pdf"}
    chat_id, filename, content, caption = sender.sent[0]
    assert (chat_id, filename) == (778, "bina-contract-2026-11-01.pdf")
    assert content.startswith(b"%PDF")
    assert caption.startswith("Lease agreement (Georgian + English)")

    file = await client.post(
        url, json={**body, "delivery": "file", "second_language": "ru"}, headers=headers("en")
    )
    assert file.status_code == 200
    assert file.headers["content-type"] == "application/pdf"
    assert file.content.startswith(b"%PDF")
    assert len(sender.sent) == 1

    bad = await client.post(url, json={**body, "payment_day": 31}, headers=headers("en"))
    assert bad.status_code == 422
    missing = await client.post(url, json={"months": 12}, headers=headers("en"))
    assert missing.status_code == 422


async def test_contract_caption_in_user_language(
    client: AsyncClient, session: AsyncSession, sender: FakeSender
) -> None:
    listing = await ListingsRepository(session).create_or_update_from_raw(
        RawListing(
            source_id="c2",
            source_name="ss",
            title="Квартира",
            description="",
            price=900,
            currency="USD",
            rooms=1,
            area=40,
            district="Ваке",
            url="https://ss.example/c2",
        )
    )
    await session.commit()
    # Первый запрос создаёт пользователя; затем делаем его Premium
    await client.post(f"/api/listings/{listing.id}/contract", json=BODY, headers=headers("ru"))
    await make_premium(session)
    answer = await client.post(
        f"/api/listings/{listing.id}/contract",
        json={**BODY, "address": "Палиашвили 1"},
        headers=headers("ru"),
    )
    assert answer.status_code == 200
    assert sender.sent[-1][3].startswith("Договор аренды (грузинский + русский)")


async def test_premium_for_all_opens_contract(
    client: AsyncClient,
    session: AsyncSession,
    sender: FakeSender,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Режим тестирования: договор доступен и без оплаты."""
    monkeypatch.setenv("PREMIUM_FOR_ALL", "1")
    listing = await ListingsRepository(session).create_or_update_from_raw(
        RawListing(
            source_id="c3",
            source_name="ss",
            title="Квартира",
            description="",
            price=1000,
            currency="GEL",
            rooms=2,
            area=50,
            district="Ваке",
            url="https://ss.example/c3",
        )
    )
    await session.commit()
    answer = await client.post(
        f"/api/listings/{listing.id}/contract",
        json={**BODY, "address": "Paliashvili 1"},
        headers=headers("en"),
    )
    assert answer.status_code == 200
    assert len(sender.sent) == 1


async def test_contract_for_signing(
    client: AsyncClient, session: AsyncSession, sender: FakeSender
) -> None:
    """TASK-115: договор на подпись — сохранён, создателю в чат со ссылкой для второй стороны."""
    listing = await ListingsRepository(session).create_or_update_from_raw(
        RawListing(
            source_id="sign-1",
            source_name="ss",
            title="Квартира",
            description="",
            price=1500,
            currency="GEL",
            rooms=2,
            area=60,
            district="Ваке",
            url="https://ss.example/sign-1",
            address="ул. Чавчавадзе, 10",
        )
    )
    await session.commit()
    client_app = client._transport.app  # type: ignore[attr-defined]
    client_app.state.bot_username = "bina_bot"
    await client.get("/api/me", headers=headers("ru"))
    await make_premium(session)

    answer = await client.post(
        f"/api/listings/{listing.id}/contract",
        json={**BODY, "delivery": "sign"},
        headers=headers("ru"),
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["sent"] is True
    assert body["invite_url"].startswith("https://t.me/bina_bot?start=sign_")
    [(chat_id, filename, content, caption)] = sender.sent
    assert filename.startswith("bina-contract-")
    assert chat_id == 778 and content.startswith(b"%PDF") and body["invite_url"] in caption

    documents = (await client.get("/api/documents", headers=headers("ru"))).json()["items"]
    [document] = documents
    assert document["status"] == "pending" and document["invite_url"] == body["invite_url"]
    assert document["title"].startswith("Договор аренды: Giorgi Beridze — Anna Smith")

    file = await client.get(
        f"/api/documents/{document['id']}/file", params={"delivery": "file"}, headers=headers("ru")
    )
    assert file.status_code == 200 and file.content == content
    certificate = await client.get(
        f"/api/documents/{document['id']}/file",
        params={"part": "certificate", "delivery": "file"},
        headers=headers("ru"),
    )
    assert certificate.status_code == 409, "сертификат — только когда подписали оба"
    stranger = {
        "X-Telegram-Init-Data": sign_init_data(
            BOT_TOKEN, {"id": 999, "first_name": "X", "language_code": "ru"}
        )
    }
    other = await client.get(f"/api/documents/{document['id']}/file", headers=stranger)
    assert other.status_code == 404, "чужой документ не отдаём"
