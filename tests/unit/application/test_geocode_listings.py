"""Точки на карте по адресу (TASK-080)."""

from types import SimpleNamespace
from uuid import UUID, uuid4

from bina.application.ports.geocoder import GeocoderError
from bina.application.use_cases.geocode_listings import GeocodeListingsUseCase
from bina.infrastructure.db.models import Listing


class FakeRepository:
    def __init__(self, addresses: list[str]) -> None:
        self.listings = [SimpleNamespace(id=uuid4(), address=address) for address in addresses]
        self.saved: dict[str, tuple[float, float] | None] = {}

    async def to_geocode(self, limit: int) -> list[Listing]:
        return self.listings[:limit]  # type: ignore[return-value]

    async def save_location(self, listing_id: UUID, location: tuple[float, float] | None) -> None:
        address = next(item.address for item in self.listings if item.id == listing_id)
        self.saved[address] = location


ANSWERS: dict[str, tuple[float, float] | None] = {
    "Paliashvili 1": (41.709, 44.758),
    "Nowhere 5": None,
    "Batumi Ave 1": (41.6168, 41.6367),  # не Тбилиси
}


class FakeGeocoder:
    def __init__(self) -> None:
        self.cities: list[str] = []

    async def locate(self, address: str, city: str) -> tuple[float, float] | None:
        self.cities.append(city)
        if address == "Broken 1":
            raise GeocoderError("timeout")
        return ANSWERS[address]


async def test_geocode() -> None:
    repository = FakeRepository(["Paliashvili 1", "Nowhere 5", "Batumi Ave 1", "Broken 1"])
    geocoder = FakeGeocoder()

    stats = await GeocodeListingsUseCase(repository, geocoder).execute(10)

    assert (stats.checked, stats.found, stats.failed) == (3, 1, 1)
    assert repository.saved == {
        "Paliashvili 1": (41.709, 44.758),
        "Nowhere 5": None,
        "Batumi Ave 1": None,
    }, "ошибка сервиса не отмечается — попробуем в следующий раз"
    assert set(geocoder.cities) == {"Tbilisi"}
