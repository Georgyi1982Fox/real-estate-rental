"""Перевод на лету при открытии объявления (TASK-010) на настоящем PostgreSQL."""

from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.application.ports.translator import ITranslator, ListingText, TranslationError
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
RU_USER = {
    "X-Telegram-Init-Data": sign_init_data(
        BOT_TOKEN, {"id": 778, "first_name": "Nino", "language_code": "ru"}
    )
}


class FakeTranslator(ITranslator):
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []
        self.fail = False

    async def translate(
        self, text: ListingText, source: str, targets: Sequence[str]
    ) -> dict[str, ListingText]:
        self.calls.append((source, list(targets)))
        if self.fail:
            raise TranslationError("boom")
        return {
            code: ListingText(f"{code}: {text.title}", f"{code}: {text.description}")
            for code in targets
        }


def georgian(source_id: str) -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="ss",
        title="ბინა ვაკეში",
        description="მზიანი ბინა ვაკეში, ახალი რემონტით",
        price=1500,
        currency="GEL",
        rooms=2,
        area=60.0,
        district="ვაკე",
        url=f"https://ss.example/{source_id}",
    )


@pytest.fixture
def fake() -> FakeTranslator:
    return FakeTranslator()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession], fake: FakeTranslator
) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    app.state.translator = fake
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def stored(session: AsyncSession, listing: Listing) -> Listing:
    await session.refresh(listing)
    return listing


async def test_user_gets_description_in_own_language(
    client: AsyncClient, session: AsyncSession, fake: FakeTranslator
) -> None:
    listing = await ListingsRepository(session).create_or_update_from_raw(georgian("tr1"))
    await session.commit()

    response = await client.get(f"/api/listings/{listing.id}", headers=RU_USER)

    assert response.status_code == 200
    body = response.json()
    assert body["description"]["ru"] == "ru: მზიანი ბინა ვაკეში, ახალი რემონტით"
    assert body["description"]["en"].startswith("en: ")
    assert fake.calls == [("ka", ["ru", "en"])]
    saved = await stored(session, listing)
    assert saved.description_ru == "ru: მზიანი ბინა ვაკეში, ახალი რემონტით"

    # Второй раз уже переведено — AI не зовём
    await client.get(f"/api/listings/{listing.id}", headers=RU_USER)
    assert len(fake.calls) == 1


async def test_guest_language_from_query_and_browser(
    client: AsyncClient, session: AsyncSession, fake: FakeTranslator
) -> None:
    repository = ListingsRepository(session)
    first = await repository.create_or_update_from_raw(georgian("tr2"))
    second = await repository.create_or_update_from_raw(georgian("tr3"))
    await session.commit()

    by_query = await client.get(f"/api/listings/{first.id}?lang=en")
    by_header = await client.get(
        f"/api/listings/{second.id}", headers={"Accept-Language": "ru-RU,ru;q=0.9"}
    )

    assert by_query.json()["description"]["en"].startswith("en: ")
    assert by_header.json()["description"]["ru"].startswith("ru: ")
    assert len(fake.calls) == 2


async def test_viewer_language_present_no_translation(
    client: AsyncClient, session: AsyncSession, fake: FakeTranslator
) -> None:
    listing = await ListingsRepository(session).create_or_update_from_raw(georgian("tr4"))
    await session.commit()

    response = await client.get(f"/api/listings/{listing.id}?lang=ka")

    assert response.status_code == 200
    assert fake.calls == []


async def test_failure_returns_listing_and_is_not_retried(
    client: AsyncClient, session: AsyncSession, fake: FakeTranslator
) -> None:
    fake.fail = True
    listing = await ListingsRepository(session).create_or_update_from_raw(georgian("tr5"))
    await session.commit()

    response = await client.get(f"/api/listings/{listing.id}", headers=RU_USER)

    assert response.status_code == 200
    assert response.json()["description"]["ka"] == "მზიანი ბინა ვაკეში, ახალი რემონტით"
    saved = await stored(session, listing)
    assert saved.translation_failed_at is not None
    assert saved.translation_failed_at <= datetime.now(UTC)

    # Сразу после сбоя не повторяем на каждом открытии
    await client.get(f"/api/listings/{listing.id}", headers=RU_USER)
    assert len(fake.calls) == 1
