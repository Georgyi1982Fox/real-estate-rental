"""Гостиницы (TASK-120): отдельный раздел, объекты размещают сами пользователи.

Гостям (вход не нужен, кроме контактов и жалоб):

- ``GET /api/hotels/options`` — коды типов, номеров и удобств (тексты — на фронтенде);
- ``GET /api/hotels`` — поиск: ``city``, ``kind`` (через запятую), ``guests``,
  ``price_min``/``price_max`` (лари за ночь), ``stars``, ``amenities`` (через запятую),
  ``sort`` (newest, price_asc, price_desc, stars_desc), ``page``/``per_page``;
- ``GET /api/hotels/{id}`` — объект целиком с номерами;
- ``GET /api/hotels/{id}/contact`` — телефон, WhatsApp, Telegram (нужен вход);
- ``POST /api/hotels/{id}/complaints`` — жалоба (3 человека — объект скрыт).

Хозяину (``/api/my/hotels``): список, разместить, изменить, снять/вернуть, удалить,
фото (тело запроса — файл, по одному, до 20), номера.
"""

from datetime import UTC, datetime
from typing import Annotated, Any, NoReturn
from uuid import UUID

import structlog
from aiogram import Bot
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from bina.application.complaints import DAILY_LIMIT as COMPLAINTS_PER_DAY
from bina.application.hotels import (
    AMENITIES,
    CURRENCIES,
    DAILY_LIMIT,
    DESCRIPTION_MAX,
    GUESTS_MAX,
    KINDS,
    LIMIT_REACHED,
    MAX_ACTIVE_HOTELS,
    MAX_PHOTOS,
    MAX_ROOMS,
    NAME_MAX,
    NO_CONTACT,
    NOT_FOUND,
    REJECTED,
    ROOM_KINDS,
    HotelDraft,
    HotelError,
    RoomDraft,
    clean_amenities,
    clean_time,
)
from bina.application.owner_listings import clean_phone, in_georgia, telegram_contact
from bina.application.use_cases.hotels import HotelsUseCase
from bina.infrastructure.api.delivery import ui_language
from bina.infrastructure.api.dependencies import (
    CurrentUserDep,
    SessionDep,
    SettingsDep,
    TelegramUsernameDep,
)
from bina.infrastructure.api.routes.common import bad_request, not_found, valid_city
from bina.infrastructure.api.routes.complaints import THANKS, ComplaintIn, ComplaintOut
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.bot.hotel_alerts import notify_admins_hotel
from bina.infrastructure.db.models import Hotel, HotelRoom, User
from bina.infrastructure.db.repositories.hotels import (
    SORTS,
    HotelEditor,
    HotelFilters,
    HotelsRepository,
)
from bina.infrastructure.storage.photos import MAX_PHOTO_BYTES, LocalPhotoStorage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/hotels", tags=["hotels"])
my_router = APIRouter(prefix="/api/my/hotels", tags=["hotels"])

MAX_PER_PAGE = 50


# ---------------------------------------------------------------- схемы


class RoomIn(BaseModel):
    kind: str = Field(description="Тип номера: " + ", ".join(ROOM_KINDS))
    title: str = Field(default="", max_length=120, description="Своё название, если нужно")
    guests: int = Field(ge=1, le=GUESTS_MAX)
    price: float = Field(gt=0, description="Цена за ночь")
    currency: str = Field(default="GEL", description="GEL, USD или EUR")
    count: int = Field(default=1, ge=1, le=500, description="Сколько таких номеров")

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str) -> str:
        if value not in ROOM_KINDS:
            raise ValueError(f"kind must be one of {', '.join(ROOM_KINDS)}")
        return value

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        if value not in CURRENCIES:
            raise ValueError(f"currency must be one of {', '.join(CURRENCIES)}")
        return value

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return clean_text(value)

    def draft(self) -> RoomDraft:
        return RoomDraft(
            kind=self.kind,
            title=self.title,
            guests=self.guests,
            price=self.price,
            currency=self.currency,
            count=self.count,
        )


class HotelIn(BaseModel):
    kind: str = Field(description="Тип объекта: " + ", ".join(KINDS))
    name: str = Field(min_length=1, max_length=NAME_MAX)
    city: str
    description: str = Field(max_length=DESCRIPTION_MAX, description="На любом языке")
    address: str | None = Field(default=None, max_length=200)
    latitude: float | None = None
    longitude: float | None = None
    stars: int | None = Field(default=None, ge=1, le=5)
    amenities: list[str] = Field(default_factory=list, description=", ".join(AMENITIES))
    check_in: str | None = Field(default=None, description="ЧЧ:ММ, например 14:00")
    check_out: str | None = Field(default=None, description="ЧЧ:ММ, например 12:00")
    phone: str | None = Field(default=None, description="Без Telegram-имени — обязателен")
    whatsapp: str | None = None
    rooms: list[RoomIn] = Field(default_factory=list, max_length=MAX_ROOMS)

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str) -> str:
        if value not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}")
        return value

    @field_validator("name", "description", "address")
    @classmethod
    def _clean(cls, value: str | None) -> str | None:
        return clean_text(value) if value is not None else None


class RoomOut(BaseModel):
    id: UUID
    kind: str
    title: str
    guests: int
    price: float
    currency: str
    count: int

    @classmethod
    def build(cls, room: HotelRoom) -> "RoomOut":
        return cls(
            id=room.id,
            kind=room.kind,
            title=room.title,
            guests=room.guests,
            price=float(room.price),
            currency=room.currency,
            count=room.count,
        )


class HotelCardOut(BaseModel):
    """Объект в списке поиска."""

    id: UUID
    kind: str
    name: str
    city: str
    address: str | None
    stars: int | None
    amenities: list[str]
    images: list[str]
    min_price: float | None = Field(description="Цена ночи «от», в лари")
    max_guests: int
    latitude: float | None
    longitude: float | None
    is_promoted: bool
    is_verified: bool

    @classmethod
    def build(cls, hotel: Hotel, now: datetime) -> "HotelCardOut":
        return cls(
            id=hotel.id,
            kind=hotel.kind,
            name=hotel.name,
            city=hotel.city,
            address=hotel.address,
            stars=hotel.stars,
            amenities=list(hotel.amenities or []),
            images=list(hotel.images or []),
            min_price=float(hotel.min_price_gel) if hotel.min_price_gel is not None else None,
            max_guests=hotel.max_guests,
            latitude=hotel.latitude,
            longitude=hotel.longitude,
            is_promoted=bool(hotel.promoted_until and hotel.promoted_until > now),
            is_verified=hotel.is_verified,
        )


class HotelOut(HotelCardOut):
    """Объект целиком."""

    description: dict[str, str] = Field(description="ka/ru/en: какие языки уже есть")
    check_in: str | None
    check_out: str | None
    rooms: list[RoomOut]
    has_phone: bool
    has_whatsapp: bool
    has_telegram: bool

    @classmethod
    def full(cls, hotel: Hotel, now: datetime) -> "HotelOut":
        card = HotelCardOut.build(hotel, now)
        return cls(
            **card.model_dump(),
            description={
                code: text
                for code in ("ka", "ru", "en")
                if (text := getattr(hotel, f"description_{code}"))
            },
            check_in=hotel.check_in,
            check_out=hotel.check_out,
            rooms=[RoomOut.build(room) for room in hotel.rooms],
            has_phone=bool(hotel.phone),
            has_whatsapp=bool(hotel.whatsapp),
            has_telegram=bool(hotel.contact_url),
        )


class MyHotelOut(HotelOut):
    """Свой объект: ещё статус показа."""

    status: str = Field(description="active — в поиске, off — снят, hidden — скрыт модерацией")
    phone: str | None
    whatsapp: str | None

    @classmethod
    def mine(cls, hotel: Hotel, now: datetime) -> "MyHotelOut":
        if hotel.hidden_at is not None:
            state = "hidden"
        elif not hotel.is_active:
            state = "off"
        else:
            state = "active"
        return cls(
            **HotelOut.full(hotel, now).model_dump(),
            status=state,
            phone=hotel.phone,
            whatsapp=hotel.whatsapp,
        )


class HotelsPageOut(BaseModel):
    items: list[HotelCardOut]
    total: int
    page: int
    pages: int


class MyHotelsOut(BaseModel):
    items: list[MyHotelOut]
    limit: int


class ActiveIn(BaseModel):
    active: bool


class ContactOut(BaseModel):
    phone: str | None
    whatsapp_url: str | None
    telegram_url: str | None


class OptionsOut(BaseModel):
    kinds: list[str]
    room_kinds: list[str]
    amenities: list[str]
    currencies: list[str]
    sorts: list[str]
    limits: dict[str, int]


# ---------------------------------------------------------------- гостям


@router.get("/options", response_model=OptionsOut)
async def hotel_options() -> OptionsOut:
    """Коды для форм и фильтров (тексты — на фронтенде, ka/ru/en)."""
    return OptionsOut(
        kinds=list(KINDS),
        room_kinds=list(ROOM_KINDS),
        amenities=list(AMENITIES),
        currencies=list(CURRENCIES),
        sorts=list(SORTS),
        limits={
            "active_hotels": MAX_ACTIVE_HOTELS,
            "rooms": MAX_ROOMS,
            "photos": MAX_PHOTOS,
            "description": DESCRIPTION_MAX,
        },
    )


def _codes(value: str | None, allowed: tuple[str, ...], name: str) -> tuple[str, ...]:
    codes = tuple(code for code in (value or "").split(",") if code)
    unknown = [code for code in codes if code not in allowed]
    if unknown:
        raise bad_request(f"unknown {name}: {', '.join(unknown)}")
    return codes


@router.get("", response_model=HotelsPageOut)
async def search_hotels(
    session: SessionDep,
    city: str | None = None,
    kind: str | None = None,
    guests: Annotated[int | None, Query(ge=1, le=GUESTS_MAX)] = None,
    price_min: Annotated[float | None, Query(ge=0)] = None,
    price_max: Annotated[float | None, Query(ge=0)] = None,
    stars: Annotated[int | None, Query(ge=1, le=5)] = None,
    amenities: str | None = None,
    sort: str = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=MAX_PER_PAGE)] = 20,
) -> HotelsPageOut:
    """Поиск: сначала «🔥 Топ», дальше по ``sort``."""
    if sort not in SORTS:
        raise bad_request(f"sort must be one of {', '.join(SORTS)}")
    filters = HotelFilters(
        city=valid_city(city),
        kinds=_codes(kind, KINDS, "kind"),
        guests=guests,
        price_min=price_min,
        price_max=price_max,
        stars_min=stars,
        amenities=_codes(amenities, AMENITIES, "amenities"),
    )
    now = datetime.now(UTC)
    items, total = await HotelsRepository(session).search(filters, sort, page, per_page, now)
    return HotelsPageOut(
        items=[HotelCardOut.build(hotel, now) for hotel in items],
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
    )


async def _visible_or_404(session: SessionDep, hotel_id: UUID) -> Hotel:
    hotel = await HotelsRepository(session).get_visible(hotel_id)
    if hotel is None:
        raise not_found()
    return hotel


@router.get("/{hotel_id}", response_model=HotelOut)
async def get_hotel(hotel_id: UUID, session: SessionDep) -> HotelOut:
    return HotelOut.full(await _visible_or_404(session, hotel_id), datetime.now(UTC))


@router.get("/{hotel_id}/contact", response_model=ContactOut)
async def hotel_contact(hotel_id: UUID, user: CurrentUserDep, session: SessionDep) -> ContactOut:
    """Телефон и ссылки для связи (только после входа — защита от сборщиков номеров)."""
    hotel = await _visible_or_404(session, hotel_id)
    whatsapp = "".join(char for char in hotel.whatsapp or "" if char.isdigit())
    return ContactOut(
        phone=hotel.phone,
        whatsapp_url=f"https://wa.me/{whatsapp}" if whatsapp else None,
        telegram_url=hotel.contact_url,
    )


@router.post("/{hotel_id}/complaints", response_model=ComplaintOut)
async def complain_hotel(
    hotel_id: UUID, body: ComplaintIn, user: CurrentUserDep, session: SessionDep
) -> ComplaintOut:
    """Жалоба на объект; от 3 разных людей — объект скрыт до решения модератора."""
    await _visible_or_404(session, hotel_id)
    repository = HotelsRepository(session)
    if await repository.complaints_today(user.id, datetime.now(UTC)) >= COMPLAINTS_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many complaints today"
        )
    await repository.complain(hotel_id, user.id, body.reason.value, body.comment)
    await session.commit()
    return ComplaintOut(accepted=True, message=THANKS[ui_language(user)])


# ---------------------------------------------------------------- хозяину


def _use_case(session: SessionDep) -> HotelsUseCase:
    return HotelsUseCase(HotelsRepository(session), HotelEditor(), LocalPhotoStorage())


def _raise(error: HotelError) -> NoReturn:
    if error.code == NOT_FOUND:
        raise not_found() from error
    if error.code == LIMIT_REACHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"At most {MAX_ACTIVE_HOTELS} active hotels: take one down first",
        ) from error
    if error.code == DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many new hotels today: try again tomorrow",
        ) from error
    if error.code == NO_CONTACT:
        raise bad_request("phone is required when you have no Telegram username") from error
    if error.code == REJECTED:
        # Коды причин — в сообщении: «rejected: link_in_text,bad_price»
        raise bad_request(f"{REJECTED}: {','.join(error.reasons)}") from error
    raise bad_request(error.code) from error


def _draft(body: HotelIn, username: str | None) -> HotelDraft:
    valid_city(body.city)
    phone = clean_phone(body.phone) if body.phone else None
    if body.phone and phone is None:
        raise bad_request("phone looks invalid")
    whatsapp = clean_phone(body.whatsapp) if body.whatsapp else None
    if body.whatsapp and whatsapp is None:
        raise bad_request("whatsapp looks invalid")
    if (body.latitude is None) != (body.longitude is None):
        raise bad_request("latitude and longitude go together")
    if body.latitude is not None and body.longitude is not None:
        if not in_georgia(body.latitude, body.longitude):
            raise bad_request("the point must be in Georgia")
    for name, value in (("check_in", body.check_in), ("check_out", body.check_out)):
        if value and clean_time(value) is None:
            raise bad_request(f"{name} must look like 14:00")
    unknown = [code for code in body.amenities if code not in AMENITIES]
    if unknown:
        raise bad_request(f"unknown amenities: {', '.join(unknown)}")
    return HotelDraft(
        kind=body.kind,
        name=body.name,
        city=body.city,
        description=body.description,
        address=body.address,
        latitude=body.latitude,
        longitude=body.longitude,
        stars=body.stars,
        amenities=clean_amenities(body.amenities),
        check_in=clean_time(body.check_in),
        check_out=clean_time(body.check_out),
        phone=phone,
        whatsapp=whatsapp,
        contact_url=telegram_contact(username),
        rooms=tuple(room.draft() for room in body.rooms),
    )


@my_router.get("", response_model=MyHotelsOut)
async def list_my_hotels(user: CurrentUserDep, session: SessionDep) -> MyHotelsOut:
    now = datetime.now(UTC)
    hotels = await HotelsRepository(session).list_for_owner(user.id)
    return MyHotelsOut(
        items=[MyHotelOut.mine(hotel, now) for hotel in hotels], limit=MAX_ACTIVE_HOTELS
    )


@my_router.post("", response_model=MyHotelOut, status_code=status.HTTP_201_CREATED)
async def create_hotel(
    body: HotelIn,
    user: CurrentUserDep,
    username: TelegramUsernameDep,
    session: SessionDep,
    settings: SettingsDep,
) -> MyHotelOut:
    """Разместить объект: сразу в поиске, если прошёл проверку и есть номер с ценой.

    422 с сообщением ``rejected: <коды через запятую>`` — не прошёл проверку: ``link_in_text``,
    ``contact_in_text`` (телефон/почта в описании), ``bad_name``, ``bad_description``,
    ``bad_price`` (ночь дешевле 10 ₾ или дороже 5 000 ₾).
    """
    now = datetime.now(UTC)
    try:
        hotel = await _use_case(session).publish(user.id, _draft(body, username), now)
    except HotelError as exc:
        _raise(exc)
    await session.commit()
    await session.refresh(hotel)
    await _alert(settings, hotel, user)
    return MyHotelOut.mine(hotel, now)


async def _owned(session: SessionDep, user: User, hotel_id: UUID) -> Hotel:
    try:
        hotel: Hotel = await _use_case(session).owned(user.id, hotel_id)
    except HotelError as exc:
        _raise(exc)
    return hotel


@my_router.get("/{hotel_id}", response_model=MyHotelOut)
async def get_my_hotel(hotel_id: UUID, user: CurrentUserDep, session: SessionDep) -> MyHotelOut:
    return MyHotelOut.mine(await _owned(session, user, hotel_id), datetime.now(UTC))


async def _saved(session: SessionDep, hotel: Any) -> MyHotelOut:
    await session.commit()
    await session.refresh(hotel)
    return MyHotelOut.mine(hotel, datetime.now(UTC))


@my_router.put("/{hotel_id}", response_model=MyHotelOut)
async def update_hotel(
    hotel_id: UUID,
    body: HotelIn,
    user: CurrentUserDep,
    username: TelegramUsernameDep,
    session: SessionDep,
) -> MyHotelOut:
    """Изменить данные объекта (номера — отдельно, ``rooms`` здесь не учитываются)."""
    try:
        hotel = await _use_case(session).update(user.id, hotel_id, _draft(body, username))
    except HotelError as exc:
        _raise(exc)
    return await _saved(session, hotel)


@my_router.patch("/{hotel_id}", response_model=MyHotelOut)
async def set_hotel_active(
    hotel_id: UUID, body: ActiveIn, user: CurrentUserDep, session: SessionDep
) -> MyHotelOut:
    """Снять с показа / вернуть (не больше 5 включённых)."""
    try:
        hotel = await _use_case(session).set_active(user.id, hotel_id, body.active)
    except HotelError as exc:
        _raise(exc)
    return await _saved(session, hotel)


@my_router.delete("/{hotel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hotel(hotel_id: UUID, user: CurrentUserDep, session: SessionDep) -> Response:
    try:
        await _use_case(session).delete(user.id, hotel_id)
    except HotelError as exc:
        _raise(exc)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@my_router.post("/{hotel_id}/photos", response_model=MyHotelOut)
async def add_hotel_photo(
    hotel_id: UUID, request: Request, user: CurrentUserDep, session: SessionDep
) -> MyHotelOut:
    """Добавить фото: тело — файл картинки (JPEG, PNG, WebP), по одному, до 20."""
    data = await request.body()
    if not data or len(data) > MAX_PHOTO_BYTES:
        raise bad_request(f"photo must be 1 byte to {MAX_PHOTO_BYTES} bytes")
    try:
        hotel = await _use_case(session).add_photo(user.id, hotel_id, data)
    except HotelError as exc:
        _raise(exc)
    return await _saved(session, hotel)


@my_router.delete("/{hotel_id}/photos/{index}", response_model=MyHotelOut)
async def delete_hotel_photo(
    hotel_id: UUID, index: int, user: CurrentUserDep, session: SessionDep
) -> MyHotelOut:
    try:
        hotel = await _use_case(session).delete_photo(user.id, hotel_id, index)
    except HotelError as exc:
        _raise(exc)
    return await _saved(session, hotel)


@my_router.post("/{hotel_id}/rooms", response_model=MyHotelOut)
async def add_room(
    hotel_id: UUID, body: RoomIn, user: CurrentUserDep, session: SessionDep
) -> MyHotelOut:
    try:
        hotel = await _use_case(session).add_room(user.id, hotel_id, body.draft())
    except HotelError as exc:
        _raise(exc)
    return await _saved(session, hotel)


@my_router.put("/{hotel_id}/rooms/{room_id}", response_model=MyHotelOut)
async def update_room(
    hotel_id: UUID, room_id: UUID, body: RoomIn, user: CurrentUserDep, session: SessionDep
) -> MyHotelOut:
    try:
        hotel = await _use_case(session).update_room(user.id, hotel_id, room_id, body.draft())
    except HotelError as exc:
        _raise(exc)
    return await _saved(session, hotel)


@my_router.delete("/{hotel_id}/rooms/{room_id}", response_model=MyHotelOut)
async def remove_room(
    hotel_id: UUID, room_id: UUID, user: CurrentUserDep, session: SessionDep
) -> MyHotelOut:
    try:
        hotel = await _use_case(session).remove_room(user.id, hotel_id, room_id)
    except HotelError as exc:
        _raise(exc)
    return await _saved(session, hotel)


async def _alert(settings: ApiSettings, hotel: Hotel, author: User) -> None:
    """Сообщение владельцу сервиса о новом объекте (без токена бота — пропускаем)."""
    if not settings.bot_token or not settings.admin_ids:
        return
    bot = Bot(token=settings.bot_token)
    try:
        await notify_admins_hotel(bot, settings.admin_ids, hotel, author)
    finally:
        await bot.session.close()
