"""Правила размещения гостиниц (TASK-120)."""

import pytest

from bina.application.hotels import (
    HotelDraft,
    RoomDraft,
    clean_amenities,
    clean_time,
    min_night_price,
    problems,
)

DESCRIPTION = "Небольшой гостевой дом у моря: сад, терраса, завтраки по утрам."


def draft(**changes: object) -> HotelDraft:
    values: dict[str, object] = {
        "kind": "guesthouse",
        "name": "Sea Breeze",
        "city": "batumi",
        "description": DESCRIPTION,
        "rooms": (RoomDraft(kind="double", guests=2, price=120),),
    }
    values.update(changes)
    return HotelDraft(**values)  # type: ignore[arg-type]


def test_clean_hotel_passes() -> None:
    assert problems(draft()) == ()


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"description": DESCRIPTION + " Бронь: t.me/seabreeze"}, "link_in_text"),
        ({"description": DESCRIPTION + " Звоните +995 599 123 456"}, "contact_in_text"),
        ({"description": DESCRIPTION + " Почта: info@sea.ge"}, "contact_in_text"),
        ({"description": "Коротко"}, "bad_description"),
        ({"name": "x"}, "bad_name"),
        ({"rooms": (RoomDraft(kind="double", guests=2, price=1),)}, "bad_price"),
        ({"rooms": (RoomDraft(kind="suite", guests=2, price=3000, currency="USD"),)}, "bad_price"),
    ],
)
def test_problems(changes: dict[str, object], reason: str) -> None:
    assert reason in problems(draft(**changes))


def test_helpers() -> None:
    assert clean_time("9:05") == "09:05"
    assert clean_time("25:00") is None
    assert clean_amenities(["pool", "wifi", "pool", "castle"]) == ("wifi", "pool")
    assert min_night_price([(120.0, "GEL"), (40.0, "USD")]) == (40.0, "USD")
