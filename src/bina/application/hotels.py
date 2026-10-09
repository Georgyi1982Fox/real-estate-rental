"""Гостиницы (TASK-120): гостиницы, гостевые дома, хостелы — размещают сами люди.

Отдельный раздел, с квартирами не смешивается. С сайтов-источников ничего не
собирается: объекты размещают хозяева, риэлторы или любой пользователь с телефоном.
Объект появляется в поиске сразу, если прошёл проверку правилами (:func:`problems`);
жалобы скрывают его так же, как квартиры (``HIDE_AFTER`` в ``complaints``).

Цены номеров — за ночь, в лари (или в долларах/евро, как указал хозяин).
"""

import re
from dataclasses import dataclass, field

# Тип объекта
HOTEL = "hotel"
GUESTHOUSE = "guesthouse"
HOSTEL = "hostel"
APART_HOTEL = "apart_hotel"
KINDS: tuple[str, ...] = (HOTEL, GUESTHOUSE, HOSTEL, APART_HOTEL)

# Тип номера
ROOM_KINDS: tuple[str, ...] = ("single", "double", "twin", "triple", "family", "suite", "dorm")

# Удобства объекта (тексты — на фронтенде)
AMENITIES: tuple[str, ...] = (
    "wifi",
    "parking",
    "breakfast",
    "pool",
    "air_conditioning",
    "kitchen",
    "restaurant",
    "airport_transfer",
    "pets_allowed",
    "sea_view",
    "mountain_view",
    "spa",
    "gym",
    "reception_24h",
    "elevator",
    "family_rooms",
)

CURRENCIES: tuple[str, ...] = ("GEL", "USD", "EUR")

# Ограничения размещения
MAX_ACTIVE_HOTELS = 5
MAX_NEW_PER_DAY = 5
MAX_ROOMS = 30
MAX_PHOTOS = 20
NAME_MIN, NAME_MAX = 2, 120
DESCRIPTION_MIN, DESCRIPTION_MAX = 30, 3000
GUESTS_MAX = 20
# Цена ночи в лари: дешевле — заглушка («1 ₾»), дороже — опечатка или не номер
NIGHT_PRICE_MIN_GEL = 10
NIGHT_PRICE_MAX_GEL = 5000
# Примерный курс для проверки цены (не для показа)
ROUGH_GEL_RATE = {"GEL": 1.0, "USD": 2.7, "EUR": 3.0}

# Коды ошибок размещения
LIMIT_REACHED = "limit_reached"
DAILY_LIMIT = "daily_limit"
NO_CONTACT = "no_contact"
NOT_FOUND = "not_found"
TOO_MANY_ROOMS = "too_many_rooms"
TOO_MANY_PHOTOS = "too_many_photos"
BAD_PHOTO = "bad_photo"
REJECTED = "rejected"

# Причины, по которым проверка правилами не пускает объект в поиск
LINK_IN_TEXT = "link_in_text"
CONTACT_IN_TEXT = "contact_in_text"
BAD_NAME = "bad_name"
BAD_DESCRIPTION = "bad_description"
BAD_PRICE = "bad_price"

# Ссылки и контакты в тексте: их обходят мимо сервиса (и это частый признак спама)
_LINK_RE = re.compile(r"https?://|www\.|t\.me/|wa\.me/|\b[\w-]+\.(?:com|ge|ru|net|org)\b", re.I)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_PHONE_RE = re.compile(r"(?:\+?995|\b5\d{2})[\s-]?\d{2,3}[\s-]?\d{2,3}[\s-]?\d{2,3}")


class HotelError(Exception):
    """Ошибка размещения: ``code`` — одна из констант выше."""

    def __init__(self, code: str, reasons: tuple[str, ...] = ()) -> None:
        super().__init__(code)
        self.code = code
        self.reasons = reasons


@dataclass(frozen=True)
class RoomDraft:
    """Номер: тип, сколько гостей, цена за ночь, сколько таких номеров."""

    kind: str
    guests: int
    price: float
    currency: str = "GEL"
    count: int = 1
    title: str = ""


@dataclass(frozen=True)
class HotelDraft:
    """Объект, как его прислал хозяин (до проверки)."""

    kind: str
    name: str
    city: str
    description: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    stars: int | None = None
    amenities: tuple[str, ...] = ()
    check_in: str | None = None
    check_out: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    contact_url: str | None = None
    rooms: tuple[RoomDraft, ...] = field(default_factory=tuple)


def night_price_gel(price: float, currency: str) -> float:
    """Цена ночи в лари по примерному курсу (только для проверки)."""
    return price * ROUGH_GEL_RATE.get(currency, 1.0)


def room_problems(room: RoomDraft) -> tuple[str, ...]:
    gel = night_price_gel(room.price, room.currency)
    if not NIGHT_PRICE_MIN_GEL <= gel <= NIGHT_PRICE_MAX_GEL:
        return (BAD_PRICE,)
    return ()


def problems(draft: HotelDraft) -> tuple[str, ...]:
    """Почему объект нельзя показать (пусто — можно). Проверка правилами, без ИИ."""
    found: list[str] = []
    name = draft.name.strip()
    if not NAME_MIN <= len(name) <= NAME_MAX or _LINK_RE.search(name):
        found.append(BAD_NAME)
    description = draft.description.strip()
    if not DESCRIPTION_MIN <= len(description) <= DESCRIPTION_MAX:
        found.append(BAD_DESCRIPTION)
    text = f"{name}\n{description}"
    if _LINK_RE.search(text):
        found.append(LINK_IN_TEXT)
    if _EMAIL_RE.search(text) or _PHONE_RE.search(text):
        found.append(CONTACT_IN_TEXT)
    for room in draft.rooms:
        found.extend(room_problems(room))
    return tuple(dict.fromkeys(found))


def clean_time(value: str | None) -> str | None:
    """«14:00» → «14:00»; неверное время — ``None``."""
    if not value:
        return None
    match = re.fullmatch(r"\s*([01]?\d|2[0-3]):([0-5]\d)\s*", value)
    return f"{int(match.group(1)):02d}:{match.group(2)}" if match else None


def clean_amenities(codes: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Только известные удобства, без повторов, в постоянном порядке."""
    wanted = set(codes)
    return tuple(code for code in AMENITIES if code in wanted)


def min_night_price(rooms: list[tuple[float, str]]) -> tuple[float, str] | None:
    """Самый дешёвый номер «от … за ночь» (в его валюте), сравнение — в лари."""
    if not rooms:
        return None
    return min(rooms, key=lambda room: night_price_gel(*room))
