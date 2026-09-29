"""Антифрод на настоящем PostgreSQL (TASK-011).

Медиана цены по району, проверка правилами + (фейковым) AI, сохранение,
скрытие из поиска, повторная проверка после изменения объявления, API и CLI.
"""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.ports.fraud import FraudVerdict, IFraudAnalyzer, ListingFacts
from bina.application.ports.scraper import RawListing
from bina.application.ports.translator import ListingText
from bina.application.use_cases.check_fraud import CheckFraudUseCase
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.locks import FRAUD_LOCK, advisory_lock
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.llm.llm_factory import LLMFactory
from bina.infrastructure.scrapers import cli as scrape_cli
from tests.integration.conftest import DATABASE_URL


def raw(
    source_id: str, price: float, *, description: str = "Хорошая квартира", photos: int = 3
) -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="ss",
        title=f"Квартира {source_id}",
        description=description,
        price=price,
        currency="USD",
        rooms=2,
        area=50.0,
        district="Ваке",
        url=f"https://home.ss.ge/ru/{source_id}",
        photos=[f"https://static.ss.ge/{source_id}-{n}.jpg" for n in range(photos)],
    )


class KeywordAnalyzer(IFraudAnalyzer):
    """«AI»: 60 баллов за слово «предоплата»; запоминает, что видел."""

    def __init__(self) -> None:
        self.seen: list[tuple[str, ListingFacts]] = []

    async def analyze(self, text: ListingText, facts: ListingFacts) -> FraudVerdict:
        self.seen.append((text.title, facts))
        if "предоплат" in text.description.lower():
            return FraudVerdict(60, ["prepayment"])
        return FraudVerdict(5, [])


async def test_fraud_check_flow(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    repository = ListingsRepository(session)
    # Рынок: 5 квартир по 1000 USD за 50 м² (20 USD/м²)
    for n in range(5):
        await repository.create_or_update_from_raw(raw(f"m{n}", 1000))
    honest = await repository.create_or_update_from_raw(raw("honest", 1100))
    cheap = await repository.create_or_update_from_raw(raw("cheap", 300, photos=0))
    scam = await repository.create_or_update_from_raw(
        raw("scam", 300, description="Срочно! Нужна предоплата на карту")
    )
    await session.commit()
    honest_id, cheap_id, scam_id = honest.id, cheap.id, scam.id

    median = await repository.district_median_per_m2(honest.district_id, "USD")
    assert median == Decimal(20)
    assert await repository.district_median_per_m2(honest.district_id, "GEL") is None
    assert len(await repository.list_fraud_unchecked(100)) == 8

    analyzer = KeywordAnalyzer()
    async with session_factory() as work:
        stats = await CheckFraudUseCase(
            analyzer, ListingsRepository(work), after_save=work.commit
        ).execute(limit=100)
    assert (stats.checked, stats.suspicious, stats.hidden, stats.failed) == (8, 1, 1, 0)
    # AI видел медиану района и число фото
    facts = dict(analyzer.seen)["Квартира cheap"]
    assert (facts.district_median_per_m2, facts.photos, facts.district) == (Decimal(20), 0, "Vake")

    session.expire_all()
    cheap_row = await repository.get_by_id(cheap_id)
    scam_row = await repository.get_by_id(scam_id)
    assert cheap_row is not None and scam_row is not None
    # 5 (AI) + 40 (цена 6 USD/м² при медиане 20) + 10 (нет фото)
    assert (cheap_row.fraud_score, cheap_row.fraud_reasons) == (
        55,
        ["price_far_below_market", "no_photos"],
    )
    assert (scam_row.fraud_score, scam_row.fraud_reasons) == (
        100,
        ["prepayment", "price_far_below_market"],
    )
    assert await repository.list_fraud_unchecked(100) == []

    # Поиск: мошенник скрыт, подозрительное видно
    found = await repository.search(ListingSearchFilters(), limit=100)
    ids = {item.id for item in found}
    assert scam_id not in ids and cheap_id in ids and honest_id in ids

    # API: уровень и причины; по прямой ссылке скрытое объявление открывается
    app = create_app(ApiSettings(), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get(f"/api/listings/{cheap_id}")).json()
        assert (body["fraud_level"], body["fraud_reasons"]) == (
            "warning",
            ["price_far_below_market", "no_photos"],
        )
        hidden = await client.get(f"/api/listings/{scam_id}")
        assert hidden.status_code == 200
        assert hidden.json()["fraud_level"] == "high"
        listing_ids = [
            item["id"] for item in (await client.get("/api/listings?per_page=50")).json()["items"]
        ]
        assert str(scam_id) not in listing_ids

    # Повторный парсинг без изменений — проверка остаётся; новая цена — проверить заново
    await repository.create_or_update_from_raw(raw("honest", 1100))
    await session.commit()
    assert await repository.list_fraud_unchecked(100) == []
    await repository.create_or_update_from_raw(raw("scam", 1000))
    await session.commit()
    assert [item.source_id for item in await repository.list_fraud_unchecked(100)] == ["scam"]


async def test_only_one_fraud_check_at_a_time(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setattr(LLMFactory, "create_provider", staticmethod(lambda: object()))
    monkeypatch.setattr(scrape_cli, "LLMFraudAnalyzer", lambda provider: KeywordAnalyzer())

    async with advisory_lock(engine, FRAUD_LOCK) as first:
        assert first
        with pytest.raises(scrape_cli.FraudCheckBusyError):
            await scrape_cli.check_fraud(10)

    stats = await scrape_cli.check_fraud(10)
    assert stats.checked == 0
