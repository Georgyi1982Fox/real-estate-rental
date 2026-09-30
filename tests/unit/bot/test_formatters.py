from decimal import Decimal
from uuid import uuid4

import pytest

from bina.infrastructure.bot.formatters import (
    district_name,
    format_listing,
    format_listings,
    format_number,
    format_price,
    listing_title,
    truncate,
)
from bina.infrastructure.db.models import District, Listing


def make_listing(**overrides: object) -> Listing:
    """Объявление с разумными значениями по умолчанию."""
    values: dict[str, object] = {
        "id": uuid4(),
        "title_ru": "Квартира",
        "title_ka": "ბინა",
        "price": Decimal(1200),
        "currency": "GEL",
        "rooms": 2,
        "area": Decimal("55.5"),
        "is_verified": False,
    }
    values.update(overrides)
    return Listing(**values)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal(1200), "1 200"),
        (Decimal("1200.00"), "1 200"),
        (Decimal("55.50"), "55.5"),
        (1234567, "1 234 567"),
        (0, "0"),
        (12.25, "12.25"),
    ],
)
def test_format_number(value: Decimal | float | int, expected: str) -> None:
    assert format_number(value) == expected


@pytest.mark.parametrize(
    ("currency", "expected"),
    [("GEL", "1 500 ₾"), ("usd", "$1 500"), ("EUR", "1 500 €"), ("RUB", "1 500 RUB")],
)
def test_format_price(currency: str, expected: str) -> None:
    assert format_price(Decimal(1500), currency) == expected


def test_truncate() -> None:
    assert truncate("короткий", 20) == "короткий"
    assert truncate("очень   длинный\nзаголовок", 12) == "очень длинн…"


@pytest.mark.parametrize(
    ("language", "title_ru", "title_ka", "expected"),
    [
        ("ru", "Квартира", "ბინა", "Квартира"),
        ("en", "Квартира", "ბინა", "Квартира"),
        ("ka", "Квартира", "ბინა", "ბინა"),
        ("ka", "Квартира", "", "Квартира"),
        ("ru", "", "ბინა", "ბინა"),
    ],
)
def test_listing_title(language: str, title_ru: str, title_ka: str, expected: str) -> None:
    listing = make_listing(title_ru=title_ru, title_ka=title_ka)
    assert listing_title(listing, language) == expected


def test_district_name_falls_back_to_russian() -> None:
    district = District(name_ru="Ваке", name_ka="ვაკე", name_en="")
    assert district_name(district, "ka") == "ვაკე"
    assert district_name(district, "en") == "Ваке"


def test_format_listing_escapes_html() -> None:
    listing = make_listing(title_ru="<b>Акция</b> & скидки", is_verified=True)

    text = format_listing(listing, 3, "ru")

    assert text == (
        "<b>3. &lt;b&gt;Акция&lt;/b&gt; &amp; скидки</b>\n💰 1 200 ₾ · 🚪 2 комн. · 📐 55.5 м² · ✅"
    )


def test_format_listings_numbering() -> None:
    text = format_listings([make_listing(), make_listing()], 6, "en")
    assert "<b>6. " in text and "<b>7. " in text
    assert "2 rooms" in text


@pytest.mark.parametrize(
    ("score", "warned"), [(None, False), (0, False), (39, False), (40, True), (95, True)]
)
def test_fraud_warning(score: int | None, warned: bool) -> None:
    listing = make_listing(fraud_score=score)
    text = format_listing(listing, 1, "ru")
    assert ("⚠️" in text) is warned
    if warned:
        assert "не платите до просмотра" in text


@pytest.mark.parametrize(
    ("language", "expected"), [("ru", "50 ₾ / сутки"), ("en", "50 ₾ / day"), ("ka", "50 ₾ / დღე")]
)
def test_daily_rent_price_is_per_day(language: str, expected: str) -> None:
    """TASK-092: у посуточной аренды цена за сутки."""
    listing = make_listing(price=Decimal(50), rent_period="daily")
    assert f"💰 {expected} · " in format_listing(listing, 1, language)
    assert "/ сутки" not in format_listing(make_listing(rent_period="monthly"), 1, "ru")
