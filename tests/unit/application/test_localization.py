"""Транслитерация имён, адресов и районов (TASK-019)."""

import pytest

from bina.application.localization import (
    district_names,
    localize_address,
    localize_name,
    script_of,
    transliterate,
)


@pytest.mark.parametrize(
    ("text", "script"), [("ნინო", "ka"), ("Вера", "ru"), ("Davit", "en"), ("123", "en")]
)
def test_script_of(text: str, script: str) -> None:
    assert script_of(text) == script


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("ნინო", {"ka": "ნინო", "ru": "Нино", "en": "Nino"}),
        ("ელენე ბერიძე", {"ka": "ელენე ბერიძე", "ru": "Элене Беридзе", "en": "Elene Beridze"}),
        ("Mikheili", {"ka": "მიხეილი", "ru": "Михеили", "en": "Mikheili"}),
        ("Мария", {"ka": "მარია", "ru": "Мария", "en": "Mariya"}),
        # Названия компаний (ЗАГЛАВНЫМИ, с цифрами) не трогаем
        (
            "REALTYSOLUTIONS",
            {"ka": "REALTYSOLUTIONS", "ru": "REALTYSOLUTIONS", "en": "REALTYSOLUTIONS"},
        ),
        ("ProHome 24", {"ka": "ProHome 24", "ru": "ProHome 24", "en": "ProHome 24"}),
    ],
)
def test_localize_name(name: str, expected: dict[str, str]) -> None:
    assert localize_name(name) == expected


def test_localize_name_empty() -> None:
    assert localize_name(None) == {}
    assert localize_name("   ") == {}


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        (
            "ცაგარელის ქუჩა 26",
            {"ka": "ცაგარელის ქუჩა 26", "ru": "ул. Цагарели 26", "en": "Tsagareli St. 26"},
        ),
        (
            "დუმბაძის გამზ. 1",
            {"ka": "დუმბაძის გამზ. 1", "ru": "просп. Думбадзе 1", "en": "Dumbadze Ave. 1"},
        ),
        ("შარტავას ქ. ", {"ka": "შარტავას ქ.", "ru": "ул. Шартава", "en": "Shartava St."}),
        (
            "ул. Мачабели 6",
            {"ka": "მაჩაბელი ქ. 6", "ru": "ул. Мачабели 6", "en": "Machabeli St. 6"},
        ),
    ],
)
def test_localize_address(address: str, expected: dict[str, str]) -> None:
    assert localize_address(address) == expected


def test_localize_address_empty() -> None:
    assert localize_address(None) == {}


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Сабуртало", {"ru": "Сабуртало", "en": "Saburtalo", "ka": "საბურთალო"}),
        ("ვაკე", {"ru": "Ваке", "en": "Vake", "ka": "ვაკე"}),
        # Опечатка сайта и номер части района
        ("Старий Тбилиси", {"ru": "Старый Тбилиси", "en": "Old Tbilisi", "ka": "ძველი თბილისი"}),
        ("Дигоми 3", {"ru": "Дигоми 3", "en": "Digomi 3", "ka": "დიღომი 3"}),
    ],
)
def test_district_names(name: str, expected: dict[str, str]) -> None:
    assert district_names(name) == expected


def test_unknown_district_is_transliterated() -> None:
    names = district_names("Новый квартал")
    assert names["ru"] == "Новый квартал"
    assert names["en"] == "Novyy kvartal"
    assert script_of(names["ka"]) == "ka"


def test_transliterate_same_script_unchanged() -> None:
    assert transliterate("Ваке", "ru") == "Ваке"
