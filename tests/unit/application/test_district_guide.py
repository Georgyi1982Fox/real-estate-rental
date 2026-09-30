"""Справка по районам (TASK-104) и центр района для карты (TASK-080)."""

from bina.application.district_guide import (
    CITY_CENTER,
    GUIDE,
    TAG_LABELS,
    distance_km,
    guide_for,
    in_tbilisi,
    minutes_to_center,
)
from bina.application.localization import district_names, script_of


def test_every_district_is_known_and_in_tbilisi() -> None:
    for name, guide in GUIDE.items():
        assert district_names(name)["en"] == name, name
        assert in_tbilisi(guide.latitude, guide.longitude), name


def test_texts_in_every_language() -> None:
    for guide in GUIDE.values():
        if guide.about:
            for language in ("ka", "ru", "en"):
                assert script_of(guide.about[language]) == language
    for labels in TAG_LABELS.values():
        for language in ("ka", "ru", "en"):
            assert script_of(labels[language]) == language


def test_guide_for_numbered_district() -> None:
    assert guide_for("Digomi 3") is GUIDE["Digomi"]
    assert guide_for("Vake") is GUIDE["Vake"]
    assert guide_for("Atlantis") is None


def test_distance_and_minutes() -> None:
    vake = GUIDE["Vake"]
    assert 3 < distance_km(vake.latitude, vake.longitude, *CITY_CENTER) < 6
    assert minutes_to_center(*CITY_CENTER) == 5
    assert minutes_to_center(vake.latitude, vake.longitude) <= 20
    gldani = GUIDE["Gldani"]
    assert minutes_to_center(gldani.latitude, gldani.longitude) > minutes_to_center(
        vake.latitude, vake.longitude
    )


def test_in_tbilisi() -> None:
    assert in_tbilisi(*CITY_CENTER)
    assert not in_tbilisi(41.6168, 41.6367)  # Батуми
