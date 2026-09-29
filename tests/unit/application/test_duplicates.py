"""Та же квартира на двух сайтах (TASK-090)."""

import dataclasses
from decimal import Decimal

import pytest

from bina.application.duplicates import distance_m, phone_key, same_apartment


@dataclasses.dataclass
class Flat:
    rooms: int = 2
    area: float = 60.0
    price: Decimal = Decimal(1500)
    currency: str = "GEL"
    floor: int | None = 5
    total_floors: int | None = 9
    bedrooms: int | None = 1
    latitude: float | None = 41.7100
    longitude: float | None = 44.7700
    phone: str | None = None


BASE = Flat()


@pytest.mark.parametrize(
    "other",
    [
        Flat(),
        Flat(area=61.5, price=Decimal(1450)),  # округление площади, цена пересчитана из $
        Flat(latitude=41.7105, longitude=44.7702),  # метка на доме со сдвигом ~60 м
        Flat(floor=None, total_floors=None, bedrooms=None),  # на одном сайте не указано
    ],
)
def test_same_apartment(other: Flat) -> None:
    assert same_apartment(BASE, other)
    assert same_apartment(other, BASE)


@pytest.mark.parametrize(
    "other",
    [
        Flat(rooms=3),
        Flat(area=70.0),
        Flat(price=Decimal(1700)),
        Flat(currency="USD"),
        Flat(floor=6),  # тот же дом, другой этаж
        Flat(total_floors=12),
        Flat(bedrooms=2),
        Flat(latitude=41.7200),  # ~1 км
    ],
)
def test_different_apartments(other: Flat) -> None:
    assert not same_apartment(BASE, other)


def test_without_coordinates_phone_and_floor_decide() -> None:
    a = Flat(latitude=None, longitude=None, phone="+995 555 12-34-56")
    assert same_apartment(a, Flat(latitude=None, longitude=None, phone="555123456"))
    assert not same_apartment(a, Flat(latitude=None, longitude=None, phone="555000000"))
    assert not same_apartment(a, Flat(latitude=None, longitude=None, phone=None))
    # Этаж неизвестен: у риелтора один телефон на много квартир
    unknown_floor = Flat(latitude=None, longitude=None, phone="555123456", floor=None)
    assert not same_apartment(dataclasses.replace(a, floor=None), unknown_floor)


def test_coordinates_beat_phone() -> None:
    """Один риелтор, похожие квартиры в разных домах — не дубликаты."""
    a = Flat(phone="555123456")
    far = Flat(phone="555123456", latitude=41.7300)
    assert not same_apartment(a, far)


def test_helpers() -> None:
    assert phone_key("+995 (555) 12-34-56") == "555123456"
    assert phone_key("12345") is None
    assert distance_m(41.71, 44.77, 41.71, 44.77) == 0
    assert 1050 < distance_m(41.71, 44.77, 41.72, 44.77) < 1150
