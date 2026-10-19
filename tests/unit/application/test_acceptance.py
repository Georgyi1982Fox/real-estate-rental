"""Акт приёмки квартиры (TASK-102): чек-лист и строки PDF."""

from datetime import date

import pytest

from bina.application.acceptance import (
    CHECKLIST,
    ITEMS,
    MAX_ITEMS,
    ROOMS,
    STATUS_LABELS,
    AcceptanceData,
    CheckedItem,
    ItemStatus,
    header_row,
    intro_rows,
    is_known_item,
    item_rows,
    meter_rows,
    room_item,
)
from bina.application.localization import script_of


def data(**changes: object) -> AcceptanceData:
    values: dict[str, object] = {
        "landlord_name": "Giorgi Beridze",
        "tenant_name": "Anna Smith",
        "address": "Chavchavadze Ave 10",
        "handover_date": date(2026, 11, 1),
        "items": (
            CheckedItem("wardrobe", ItemStatus.DEFECT, "Scratch on the door"),
            CheckedItem("entrance_door", ItemStatus.OK),
        ),
    }
    values.update(changes)
    return AcceptanceData(**values)  # type: ignore[arg-type]


def test_checklist_is_complete_in_every_language() -> None:
    assert 25 <= len(ITEMS) <= 30
    assert len(ITEMS) == sum(len(section.items) for section in CHECKLIST)
    for language in ("ka", "ru", "en"):
        for section in CHECKLIST:
            assert script_of(section.labels[language]) == language
            for item in section.items:
                assert script_of(item.labels[language]) == language, item.code
        for labels in STATUS_LABELS.values():
            assert script_of(labels[language]) == language


@pytest.mark.parametrize("second", ["ru", "en"])
def test_intro_columns_in_their_language(second: str) -> None:
    for ka, other in intro_rows(data(), second):
        assert script_of(ka) == "ka"
        assert script_of(other) == second


def test_items_follow_checklist_order() -> None:
    rows = item_rows(data(), "en")
    assert [row[0].split(" / ")[1] for row in rows] == ["Entrance door and locks", "Wardrobe"]
    assert rows[1][1].endswith("/ Defect")
    assert rows[1][2] == "Scratch on the door"
    assert header_row("ru")[1].endswith("/ Состояние")


def test_meters_skip_empty_values() -> None:
    assert meter_rows(data(), "en") == []
    rows = meter_rows(data(electricity="12345", keys=0, notes="Low pressure"), "ru")
    assert [value for _, value in rows] == ["12345", "0", "Low pressure"]
    assert rows[0][0].endswith("/ Счётчик электричества")


def test_rooms_are_complete_in_every_language() -> None:
    """Комнаты (дизайн 2026-10): названия и пункты на всех языках, коды пунктов не повторяются."""
    for room in ROOMS:
        codes = [item.code for item in room.items]
        assert len(codes) == len(set(codes)), room.code
        assert room.max_count >= 1
        for language in ("ka", "ru", "en"):
            assert script_of(room.labels[language]) == language, room.code
            for item in room.items:
                assert script_of(item.labels[language]) == language, item.code
    assert MAX_ITEMS > len(ITEMS)


def test_room_item_codes() -> None:
    place = room_item("bedroom-2:windows")
    assert place is not None
    assert (place.room.code, place.number, place.item.code) == ("bedroom", 2, "windows")
    for bad in (
        "bedroom-7:windows",  # спален не больше 6
        "bedroom-0:windows",
        "bedroom-x:windows",
        "bedroom:windows",
        "bedroom-1",
        "kitchen-1:bed",  # кровать — не пункт кухни
        "attic-1:floors",
    ):
        assert room_item(bad) is None, bad
    assert is_known_item("entrance_door"), "старые коды — для черновиков до комнат"
    assert is_known_item("whole-1:cleanliness")
    assert not is_known_item("whole-2:cleanliness")


def test_room_rows_are_labelled_by_room() -> None:
    """Пункты комнат — после старых, по типам и номерам; номер — только если таких комнат две."""
    rows = item_rows(
        data(
            items=(
                CheckedItem("kitchen-1:stove", ItemStatus.OK),
                CheckedItem("bedroom-2:bed", ItemStatus.DEFECT, "Stain"),
                CheckedItem("bedroom-1:windows", ItemStatus.OK),
                CheckedItem("entrance_door", ItemStatus.OK),
            )
        ),
        "ru",
    )
    assert [row[0] for row in rows] == [
        "შესასვლელი კარი და საკეტები / Входная дверь и замки",
        "საძინებელი 1 — ფანჯრები და რაფები / Спальня 1 — Окна и подоконники",
        "საძინებელი 2 — საწოლი და ლეიბი / Спальня 2 — Кровать и матрас",
        "სამზარეულო — ქურა და ღუმელი / Кухня — Плита и духовка",
    ]
    assert rows[2][2] == "Stain"
