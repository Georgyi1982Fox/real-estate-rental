"""AI-разбор фото (TASK-114) на настоящем PostgreSQL: пачкой, значок для всех, Premium."""

from collections.abc import AsyncIterator, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.photo_analysis import PhotoReport
from bina.application.ports.photo_analyzer import IPhotoAnalyzer, PhotoAnalysisError
from bina.application.ports.scraper import RawListing
from bina.application.use_cases.analyze_photos import AnalyzePhotosUseCase
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.bot.formatters import format_listing
from bina.infrastructure.db.models import Listing, User
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.photo_reports import PhotoReportsRepository
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
HEADERS = {
    "X-Telegram-Init-Data": sign_init_data(
        BOT_TOKEN, {"id": 777, "first_name": "Nino", "language_code": "ru"}
    )
}
REPORT = PhotoReport(
    level="needs_repair",
    issues=("mold", "old_plumbing"),
    summary={"ru": "Старый ремонт, в ванной плесень.", "en": "Old.", "ka": "ძველი."},
)


class FakeAnalyzer(IPhotoAnalyzer):
    model = "fake-vision"

    def __init__(self, fail: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.fail = fail

    async def analyze(self, images: Sequence[str]) -> PhotoReport:
        self.calls.append(list(images))
        if self.fail:
            raise PhotoAnalysisError("down")
        return REPORT


def raw(source_id: str, photos: int = 2) -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="ss",
        title=f"Квартира {source_id}",
        description="Описание квартиры",
        price=1000,
        currency="GEL",
        rooms=2,
        area=60,
        district="Ваке",
        url=f"https://ss.example/{source_id}",
        photos=[f"https://cdn.example/{source_id}/{n}.jpg" for n in range(photos)],
    )


async def add(session: AsyncSession, source_id: str, photos: int = 2) -> Listing:
    listing = await ListingsRepository(session).create_or_update_from_raw(raw(source_id, photos))
    await session.commit()
    return listing


@pytest.fixture
def analyzer() -> FakeAnalyzer:
    return FakeAnalyzer()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    analyzer: FakeAnalyzer,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("PREMIUM_FOR_ALL", "0")
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    app.state.photo_analyzer = analyzer
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def make_premium(client: AsyncClient, session: AsyncSession) -> None:
    await client.get("/api/me", headers=HEADERS)  # пользователь создаётся при первом запросе
    await session.execute(
        update(User)
        .where(User.telegram_id == 777)
        .values(
            subscription_tier=SubscriptionTier.NOMAD,
            subscription_expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await session.commit()


async def test_batch_analyzes_new_listings_once(session: AsyncSession) -> None:
    with_photos = await add(session, "a")
    await add(session, "no-photos", photos=0)
    analyzer = FakeAnalyzer()
    use_case = AnalyzePhotosUseCase(PhotoReportsRepository(session), analyzer, "fake")

    stats = await use_case.execute(limit=10)
    await session.commit()
    again = await use_case.execute(limit=10)

    assert (stats.analyzed, stats.failed, again.analyzed) == (1, 0, 0)
    assert analyzer.calls == [with_photos.images]
    await session.refresh(with_photos)
    assert with_photos.repair_level == "needs_repair"
    assert "🛠 нужен ремонт" in format_listing(with_photos, 1, "ru")


async def test_batch_failure_is_retried_later(session: AsyncSession) -> None:
    await add(session, "a")
    repository = PhotoReportsRepository(session)
    failed = await AnalyzePhotosUseCase(repository, FakeAnalyzer(fail=True)).execute(10)
    assert (failed.analyzed, failed.failed) == (0, 1)
    assert len(await repository.listings_without_report(10)) == 1


async def test_free_user_sees_level_only(
    client: AsyncClient, session: AsyncSession, analyzer: FakeAnalyzer
) -> None:
    listing = await add(session, "a")
    response = await client.get(f"/api/listings/{listing.id}/photo-report", headers=HEADERS)
    assert response.status_code == 404, "ещё не разобрано, без Premium по запросу не разбираем"
    assert analyzer.calls == []

    await AnalyzePhotosUseCase(PhotoReportsRepository(session), analyzer).execute(10)
    await session.commit()
    body = (await client.get(f"/api/listings/{listing.id}/photo-report", headers=HEADERS)).json()
    assert body["level"] == "needs_repair"
    assert body["level_label"] == "нужен ремонт"
    assert (body["issues"], body["summary"], body["premium_required"]) == ([], "", True)

    found = (await client.get("/api/listings", headers=HEADERS)).json()
    assert found["items"][0]["repair_level"] == "needs_repair"


async def test_premium_gets_details_and_on_demand_analysis(
    client: AsyncClient, session: AsyncSession, analyzer: FakeAnalyzer
) -> None:
    listing = await add(session, "a")
    await make_premium(client, session)

    body = (await client.get(f"/api/listings/{listing.id}/photo-report", headers=HEADERS)).json()
    assert body["premium_required"] is False
    assert [issue["label"] for issue in body["issues"]] == ["Плесень", "Старая сантехника"]
    assert body["summary"] == "Старый ремонт, в ванной плесень."
    assert len(analyzer.calls) == 1

    # Повторно — из базы; поменялись фото — разбор заново
    await client.get(f"/api/listings/{listing.id}/photo-report", headers=HEADERS)
    assert len(analyzer.calls) == 1
    changed = replace(raw("a"), photos=["https://cdn.example/a/new.jpg"])
    await ListingsRepository(session).create_or_update_from_raw(changed)
    await session.commit()
    await client.get(f"/api/listings/{listing.id}/photo-report", headers=HEADERS)
    assert len(analyzer.calls) == 2


async def test_listing_without_photos(client: AsyncClient, session: AsyncSession) -> None:
    listing = await add(session, "a", photos=0)
    await make_premium(client, session)
    response = await client.get(f"/api/listings/{listing.id}/photo-report", headers=HEADERS)
    assert response.status_code == 404
