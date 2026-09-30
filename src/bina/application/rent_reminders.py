"""Напоминания об оплате аренды (TASK-109).

Пользователь указывает день месяца (1-28) и сумму. Бот напоминает за 3 дня, за
1 день и в день оплаты — по времени Тбилиси, не раньше ``SEND_FROM_HOUR`` утра.
Кнопка «Оплачено» останавливает напоминания до следующего месяца.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

TBILISI = ZoneInfo("Asia/Tbilisi")
SEND_FROM_HOUR = 10
REMIND_DAYS_BEFORE = (3, 1, 0)
MAX_REMINDERS = 3
MAX_DAY = 28  # в каждом месяце есть 28-е число

_CURRENCIES = {
    "$": "USD",
    "usd": "USD",
    "дол": "USD",
    "€": "EUR",
    "eur": "EUR",
    "евро": "EUR",
    "₾": "GEL",
    "gel": "GEL",
    "лар": "GEL",
    "ლარ": "GEL",
}
_AMOUNT_RE = re.compile(r"\d[\d\s.,]*")


def parse_amount(text: str) -> tuple[Decimal, str] | None:
    """«1500», «1 500 лари», «700 $», «$700», «650 eur» → (сумма, валюта); лари по умолчанию."""
    match = _AMOUNT_RE.search(text or "")
    if match is None or text[: match.start()].rstrip().endswith("-"):
        return None
    digits = re.sub(r"\s", "", match.group()).rstrip(".,")
    # «1.500» и «1,500» — тысячи; «1500.50» — копейки
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", digits):
        digits = re.sub(r"[.,]", "", digits)
    try:
        amount = Decimal(digits.replace(",", "."))
    except InvalidOperation:
        return None
    if amount <= 0 or amount > 1_000_000:
        return None
    rest = text.lower()
    currency = next((code for key, code in _CURRENCIES.items() if key in rest), "GEL")
    return amount, currency


def local_now(now: datetime) -> datetime:
    return now.astimezone(TBILISI)


def next_due(today: date, day: int) -> date:
    """Ближайшая дата оплаты начиная с сегодня."""
    if today.day <= day:
        return today.replace(day=day)
    year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    return date(year, month, day)


def days_left(today: date, day: int) -> int:
    return (next_due(today, day) - today).days


def format_amount(amount: Decimal, currency: str) -> str:
    symbol = {"GEL": "₾", "USD": "$", "EUR": "€"}.get(currency, currency)
    value = f"{amount:,.2f}".rstrip("0").rstrip(".").replace(",", " ")
    return f"{value} {symbol}"
