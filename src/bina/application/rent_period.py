"""Вид аренды объявления (TASK-092): помесячно или посуточно.

У посуточной аренды цена — за сутки, поэтому объявления разных видов не
смешиваются в поиске, статистике цен и проверках: по умолчанию поиск
показывает помесячную аренду.
"""

import re

MONTHLY = "monthly"
DAILY = "daily"
RENT_PERIODS: tuple[str, ...] = (MONTHLY, DAILY)


def rent_period_code(value: object) -> str:
    """Код вида аренды; неизвестное значение — помесячно."""
    return value if isinstance(value, str) and value in RENT_PERIODS else MONTHLY


# Слова посуточной аренды в запросе умного поиска: «квартира посуточно в Ваке»
_DAILY_WORDS = re.compile(
    r"посуточ|на\s+сутки|за\s+сутки|daily|per\s+(?:day|night)|short[\s-]*term|დღიურ",
    re.IGNORECASE,
)


def period_from_text(text: str) -> str:
    """Вид аренды, о котором просит текст: «посуточно» — daily, иначе monthly."""
    return DAILY if _DAILY_WORDS.search(text) else MONTHLY
