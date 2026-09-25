import re

import pytest

from bina.infrastructure.bot.texts import TEXTS, all_variants, t, ui_language


def test_all_languages_have_same_keys() -> None:
    """В каждом переводе есть все ключи."""
    keys = {language: set(texts) for language, texts in TEXTS.items()}
    reference = keys["ru"]
    for language, language_keys in keys.items():
        assert language_keys == reference, f"{language}: {language_keys ^ reference}"


@pytest.mark.parametrize("key", sorted(TEXTS["ru"]))
def test_placeholders_match_between_languages(key: str) -> None:
    """Плейсхолдеры {name} одинаковы во всех переводах."""
    placeholders = {
        language: set(re.findall(r"{(\w+)}", texts[key])) for language, texts in TEXTS.items()
    }
    assert len({frozenset(value) for value in placeholders.values()}) == 1, placeholders


@pytest.mark.parametrize(
    ("language", "expected"),
    [("ru", "ru"), ("en", "en"), ("ka", "en"), ("de", "ru")],
)
def test_ui_language(language: str, expected: str) -> None:
    assert ui_language(language) == expected


def test_t_formats_placeholders() -> None:
    assert t("en", "page_counter", page=2, pages=5) == "Page 2 of 5"


def test_t_allows_language_as_placeholder_name() -> None:
    """``language`` первого аргумента не конфликтует с плейсхолдером {language}."""
    text = t("ru", "profile", language="English", tier="x", expires="", balance="0",
             favorites=0, since="01.01.2026")
    assert "Язык: English" in text


def test_all_variants() -> None:
    assert all_variants("menu_search") == {"🔍 Поиск", "🔍 Search"}
