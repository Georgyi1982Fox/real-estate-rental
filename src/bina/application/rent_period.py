"""Вид аренды объявления (TASK-092): помесячно или посуточно.

У посуточной аренды цена — за сутки, поэтому объявления разных видов не
смешиваются в поиске, статистике цен и проверках: по умолчанию поиск
показывает помесячную аренду.
"""

import re

MONTHLY = "monthly"
DAILY = "daily"
RENT_PERIODS: tuple[str, ...] = (MONTHLY, DAILY)

# Ошибки хозяев на сайтах-источниках (цены в лари):
# «посуточно» дороже этого за сутки — на деле цена за месяц
DAILY_PRICE_MAX_GEL = 1000
# аренда дороже этого за м² в месяц — на деле цена продажи
RENT_PER_M2_MAX_GEL = 200
# без площади: аренда дороже этого в месяц — цена продажи
RENT_MAX_GEL = 100_000


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
