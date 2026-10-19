"""«Поделиться квартирой» (TASK-073).

Ссылка ведёт в бота: ``https://t.me/<бот>?start=l_<id>`` — бот показывает карточку квартиры
с фото, ценой и кнопками (в избранное, открыть в приложении, написать хозяину). Ссылка
одинаковая для объявлений с сайтов и от хозяев и работает у любого, даже без нашего бота.
"""

from urllib.parse import quote
from uuid import UUID

SHARE_PREFIX = "l_"


def share_link(bot_username: str, listing_id: UUID) -> str:
    """Ссылка на квартиру в боте (``start``: не больше 64 символов — uuid без дефисов)."""
    return f"https://t.me/{bot_username}?start={SHARE_PREFIX}{listing_id.hex}"


def listing_from_share(payload: str | None) -> UUID | None:
    """ID квартиры из ``/start l_<id>``; другое или неверный ID — ``None``."""
    if not payload or not payload.startswith(SHARE_PREFIX):
        return None
    try:
        return UUID(payload.removeprefix(SHARE_PREFIX))
    except ValueError:
        return None


def telegram_share_url(link: str, text: str) -> str:
    """Окно Telegram «Переслать»: выбрать чат и отправить ссылку с подписью."""
    return f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(text, safe='')}"


# --- Гостиницы (TASK-120, этап 2): ``/start h_<id>`` — карточка гостиницы

HOTEL_SHARE_PREFIX = "h_"


def hotel_share_link(bot_username: str, hotel_id: UUID) -> str:
    """Ссылка на гостиницу в боте."""
    return f"https://t.me/{bot_username}?start={HOTEL_SHARE_PREFIX}{hotel_id.hex}"


def hotel_from_share(payload: str | None) -> UUID | None:
    """ID гостиницы из ``/start h_<id>``; другое или неверный ID — ``None``."""
    if not payload or not payload.startswith(HOTEL_SHARE_PREFIX):
        return None
    try:
        return UUID(payload.removeprefix(HOTEL_SHARE_PREFIX))
    except ValueError:
        return None
