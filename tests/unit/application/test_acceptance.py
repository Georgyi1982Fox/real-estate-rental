"""Акт приёмки квартиры (TASK-102): чек-лист и строки PDF."""

from datetime import date

import pytest

from bina.application.acceptance import (
    CHECKLIST,
    ITEMS,
    STATUS_LABELS,
    AcceptanceData,
    CheckedItem,
    ItemStatus,
    header_row,
    intro_rows,
    item_rows,
    meter_rows,
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
