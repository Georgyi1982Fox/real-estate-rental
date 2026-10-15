"""Проверка гостиниц на мошенничество (без AI и базы)."""

from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

from bina.application.ports.fraud import (
    FraudAnalysisError,
    FraudVerdict,
    HotelFacts,
    IHotelFraudAnalyzer,
)
from bina.application.ports.translator import ListingText
from bina.application.use_cases.check_hotels_fraud import (
    CheckHotelsFraudUseCase,
    hotel_facts,
    hotel_text,
)
from bina.infrastructure.db.models import Hotel


def hotel(**fields: object) -> Hotel:
    values: dict[str, object] = {
        "id": uuid4(),
        "kind": "hotel",
        "name": "Seaside",
        "city": "batumi",
        "min_price_gel": Decimal("120"),
        "max_guests": 4,
        "stars": 3,
        "amenities": ["wifi", "parking"],
        "images": ["a.jpg", "b.jpg"],
        "description_ka": "",
        "description_ru": "Уютный номер у моря",
        "description_en": "",
    }
    values.update(fields)
    return cast(Hotel, SimpleNamespace(**values))


class FakeAnalyzer(IHotelFraudAnalyzer):
    def __init__(self, score: int = 0, fail: bool = False) -> None:
        self.calls: list[tuple[ListingText, HotelFacts]] = []
        self.score = score
        self.fail = fail

    async def analyze_hotel(self, text: ListingText, facts: HotelFacts) -> FraudVerdict:
        self.calls.append((text, facts))
        if self.fail:
            raise FraudAnalysisError("boom")
        reasons = ["too_good"] if self.score >= 40 else []
        return FraudVerdict(score=self.score, reasons=reasons)


class FakeRepository:
    def __init__(self, hotels: list[Hotel]) -> None:
        self.hotels = hotels
        self.saved: dict[UUID, tuple[int, list[str]]] = {}

    async def list_fraud_unchecked(self, limit: int) -> list[Hotel]:
        return self.hotels[:limit]

    async def save_fraud(self, hotel_id: UUID, score: int, reasons: list[str]) -> None:
        self.saved[hotel_id] = (score, reasons)


def test_hotel_facts_and_text() -> None:
    subject = hotel()
    facts = hotel_facts(subject)
    assert (facts.kind, facts.city, facts.stars, facts.max_guests) == ("hotel", "batumi", 3, 4)
    assert facts.price_per_night_gel == Decimal("120")
    assert (facts.amenities, facts.photos) == (2, 2)
    text = hotel_text(subject)
    assert text.title == "Seaside"
    assert text.description == "Уютный номер у моря"


async def test_clean_hotel_saved_not_hidden() -> None:
    subject = hotel()
    repository = FakeRepository([subject])
    stats = await CheckHotelsFraudUseCase(FakeAnalyzer(score=10), repository).execute(10)
    assert (stats.checked, stats.hidden, stats.failed) == (1, 0, 0)
    assert repository.saved[subject.id] == (10, [])


async def test_scam_hotel_counted_hidden() -> None:
    subject = hotel()
    repository = FakeRepository([subject])
    stats = await CheckHotelsFraudUseCase(FakeAnalyzer(score=90), repository).execute(10)
    assert (stats.checked, stats.hidden, stats.suspicious) == (1, 1, 0)
    assert repository.saved[subject.id] == (90, ["too_good"])


async def test_analysis_failure_not_saved() -> None:
    repository = FakeRepository([hotel()])
    stats = await CheckHotelsFraudUseCase(FakeAnalyzer(fail=True), repository).execute(10)
    assert (stats.checked, stats.failed) == (0, 1)
    assert repository.saved == {}
