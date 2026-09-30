"""Реферальная программа (TASK-108).

- Ссылка ``https://t.me/<бот>?start=ref_<код>``: приглашённый друг получает скидку
  ``FRIEND_DISCOUNT_PERCENT``% на первую покупку Premium.
- Когда друг оплатит первый раз, пригласивший получает ``REWARD_DAYS`` дней Premium;
  не больше ``MONTHLY_REWARDS`` наград в месяц (защита от накрутки).
- Приглашённым можно стать только новому пользователю и только один раз; себя
  пригласить нельзя.
"""

import secrets
from datetime import datetime, timedelta

FRIEND_DISCOUNT_PERCENT = 20
REWARD_DAYS = 7
MONTHLY_REWARDS = 10
# Mini App: применить код можно только в первые сутки после регистрации
APPLY_WINDOW = timedelta(days=1)

START_PREFIX = "ref_"
CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # без похожих символов (l/1, o/0)
CODE_LENGTH = 8

REWARD_TEXTS: dict[str, str] = {
    "ka": "🎁 თქვენმა მეგობარმა შეიძინა Premium თქვენი ბმულით — თქვენ მიიღეთ {days} დღე "
    "Premium საჩუქრად! მოქმედებს {date}-მდე.",
    "ru": "🎁 Ваш друг купил Premium по вашей ссылке — вам {days} дней Premium в подарок! "
    "Действует до {date}.",
    "en": "🎁 Your friend bought Premium with your link — you get {days} days of Premium as "
    "a gift! Active until {date}.",
}


def new_code() -> str:
    """Случайный код приглашения."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def code_from_start(payload: str | None) -> str | None:
    """Код из параметра ``/start ref_<код>`` (или ``startapp``); ``None`` — это не приглашение."""
    if not payload or not payload.startswith(START_PREFIX):
        return None
    code = payload.removeprefix(START_PREFIX).strip().lower()
    if len(code) != CODE_LENGTH or any(char not in CODE_ALPHABET for char in code):
        return None
    return code


def discounted_price(price_stars: int) -> int:
    """Цена со скидкой другу (не меньше 1 звезды)."""
    return max(1, round(price_stars * (100 - FRIEND_DISCOUNT_PERCENT) / 100))


def invite_link(bot_username: str, code: str) -> str:
    return f"https://t.me/{bot_username}?start={START_PREFIX}{code}"


def month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
