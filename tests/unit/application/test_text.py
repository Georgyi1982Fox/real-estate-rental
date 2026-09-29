"""Очистка HTML в текстах объявлений (TASK-019)."""

import importlib.util

import pytest

from bina.application.text import html_to_text
from bina.infrastructure.scrapers.normalizer import ListingNormalizer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ქირავდება ბინა<br /> <br /> ორ ოთახიანი", "ქირავდება ბინა\n \n ორ ოთახიანი"),
        ("<p>Первый</p><p>Второй</p>", "\nПервый\n\nВторой\n"),
        ("A &amp; B &quot;C&quot;", 'A & B "C"'),
        ("Без тегов", "Без тегов"),
    ],
)
def test_html_to_text(raw: str, expected: str) -> None:
    assert html_to_text(raw) == expected


def test_normalizer_description_without_tags() -> None:
    text = ListingNormalizer.clean_multiline(
        "ქირავდება ბინა ვაკეში<br /> <br /> ბინა   14 სართულზე"
    )
    assert text == "ქირავდება ბინა ვაკეში\n\nბინა 14 სართულზე"


def test_clean_html_migration() -> None:
    spec = importlib.util.spec_from_file_location(
        "clean_html_texts", "src/bina/infrastructure/db/alembic/versions/clean_html_texts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.clean("Раз<br />Два<br/><br/>Три") == "Раз\nДва\n\nТри"
