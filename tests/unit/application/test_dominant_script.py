"""Язык текста по большинству букв (исправление переводов)."""

import pytest

from bina.application.localization import dominant_script, in_language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Квартира в районе ვაკე, рядом парк", "ru"),  # одно грузинское слово — всё равно ru
        ("ბინა ვაკეში, Wi-Fi", "ka"),
        ("Apartment near Vake park, 3 rooms", "en"),
        ("2+1, 60", None),  # букв почти нет
        ("", None),
    ],
)
def test_dominant_script(text: str, expected: str | None) -> None:
    assert dominant_script(text) == expected


def test_in_language() -> None:
    assert in_language("ბინა ვაკეში", "ka")
    assert not in_language("Квартира в Ваке", "ka")
    assert in_language("12", "ka"), "без букв не проверяем"
