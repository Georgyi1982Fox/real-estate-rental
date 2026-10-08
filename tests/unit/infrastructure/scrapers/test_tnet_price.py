"""Цена объявления TNET (MyHome.ge, Livo.ge): пересчёт сайта в лари проверяется."""

import pytest

from bina.infrastructure.scrapers.tnet import statement_price


def prices(**totals: float) -> dict[str, dict[str, float]]:
    codes = {"gel": "1", "usd": "2", "eur": "3"}
    return {codes[name]: {"price_total": value} for name, value in totals.items()}


@pytest.mark.parametrize(
    ("currency_id", "totals", "expected"),
    [
        # Пересчёт сайта сходится с ценой хозяина — берём точный курс сайта
        (2, {"gel": 1956, "usd": 750}, (1956.0, "GEL")),
        (1, {"gel": 1500, "usd": 555}, (1500.0, "GEL")),
        # Устаревший пересчёт (старая цена продажи) — цена хозяина, в лари её переведём сами
        (2, {"gel": 325488, "usd": 750, "eur": 690}, (750.0, "USD")),
        # Есть только цена хозяина
        (2, {"usd": 750}, (750.0, "USD")),
    ],
)
def test_statement_price(
    currency_id: int, totals: dict[str, float], expected: tuple[float, str]
) -> None:
    assert statement_price({"currency_id": currency_id, "price": prices(**totals)}) == expected
