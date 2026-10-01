"""Объявления собственников (TASK-096).

Собственник размещает квартиру сам — в боте (``/mylistings``) или через API Mini App.
Объявление сразу видно в поиске; его, как и объявления с сайтов, проверяет антифрод
и переводит AI, а владельцу сервиса приходит сообщение с кнопкой «Скрыть».
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from bina.application.ports.scraper import RawListing
from bina.application.rent_period import DAILY, MONTHLY

# Listing.source_name объявлений собственников
OWNER_SOURCE = "owner"
# Столько активных объявлений может быть у одного человека (защита от спама)
MAX_ACTIVE_LISTINGS = 5
MAX_PHOTOS = 10
MIN_DESCRIPTION = 20
MAX_DESCRIPTION = 3000
MAX_ROOMS = 10
MIN_AREA = 10
MAX_AREA = 1000
MAX_FLOOR = 60
# Кнопки комнат в боте: 1 (студия) … 5+
ROOM_CHOICES: tuple[int, ...] = (1, 2, 3, 4, 5)

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
# «5/9», «5 из 9», «5 of 9», «5»
_FLOOR_RE = re.compile(r"^\s*(\d{1,2})\s*(?:(?:/|из|of|-)\s*(\d{1,2}))?\s*$", re.IGNORECASE)
_TELEGRAM_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")
_PHONE_RE = re.compile(r"^\+?\d{6,15}$")


@dataclass(frozen=True, slots=True)
class OwnerListingDraft:
    """Что собственник рассказал о квартире."""

    city: str
    district: str
    rent_period: str
    price: Decimal
    currency: str
    rooms: int
    area: Decimal
    description: str
    floor: int | None = None
    total_floors: int | None = None
    phone: str | None = None
    # Ссылка для связи: t.me/<username> (имя в Telegram), если оно есть
    contact_url: str | None = None
    features: list[str] = field(default_factory=list)


def parse_area(text: str) -> Decimal | None:
    """«60», «60 м²», «72,5» → площадь в м²; вне 10-1000 — None."""
    match = _NUMBER_RE.search(text or "")
    if match is None:
        return None
    area = Decimal(match.group().replace(",", "."))
    return area if MIN_AREA <= area <= MAX_AREA else None


def parse_floor(text: str) -> tuple[int, int | None] | None:
    """«5/9», «5 из 9», «5» → (этаж, этажей в доме); неверно — None."""
    match = _FLOOR_RE.match(text or "")
    if match is None:
        return None
    floor = int(match.group(1))
    total = int(match.group(2)) if match.group(2) else None
    if floor > MAX_FLOOR or (total is not None and (total < floor or total > MAX_FLOOR)):
        return None
    return floor, total


def clean_phone(text: str) -> str | None:
    """Телефон цифрами (с «+» в начале); не похоже на телефон — None."""
    compact = re.sub(r"[\s()\-]", "", text or "")
    return compact if _PHONE_RE.match(compact) else None


def telegram_contact(username: str | None) -> str | None:
    """Ссылка «написать в Telegram» по имени пользователя."""
    if username and _TELEGRAM_USERNAME_RE.match(username):
        return f"https://t.me/{username}"
    return None


def valid_description(text: str) -> bool:
    return MIN_DESCRIPTION <= len(text.strip()) <= MAX_DESCRIPTION


def owner_raw_listing(
    draft: OwnerListingDraft, source_id: str, photos: list[str], now: datetime
) -> RawListing:
    """Объявление собственника в том же виде, что объявления с сайтов."""
    return RawListing(
        source_id=source_id,
        source_name=OWNER_SOURCE,
        # Заголовки на всех языках собирает репозиторий (listing_titles)
        title="",
        description=draft.description.strip(),
        price=float(draft.price),
        currency=draft.currency,
        rooms=draft.rooms,
        area=float(draft.area),
        district=draft.district,
        city=draft.city,
        url=draft.contact_url or "",
        photos=list(photos),
        phone=draft.phone,
        floor=draft.floor,
        total_floors=draft.total_floors,
        features=list(draft.features),
        owner_type="owner",
        published_at=now,
        updated_at=now,
        has_details=True,
        rent_period=draft.rent_period if draft.rent_period in (MONTHLY, DAILY) else MONTHLY,
    )


class OwnerListingError(Exception):
    """Объявление нельзя разместить или изменить (код — для текста пользователю)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


# Коды ошибок
LIMIT_REACHED = "limit"
NO_CONTACT = "no_contact"
NOT_FOUND = "not_found"
TOO_MANY_PHOTOS = "too_many_photos"
BAD_PHOTO = "bad_photo"
