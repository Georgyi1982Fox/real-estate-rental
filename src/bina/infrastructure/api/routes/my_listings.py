"""Объявления собственника в Mini App (TASK-096).

- ``GET /api/my/listings`` — свои объявления;
- ``POST /api/my/listings`` — разместить (сразу в поиске);
- ``PATCH /api/my/listings/{id}`` — новая цена, снять/вернуть;
- ``POST /api/my/listings/{id}/photos`` — добавить фото: тело запроса — сам файл
  (``Content-Type: image/jpeg`` и т. п.), по одному, до 10;
- ``DELETE /api/my/listings/{id}/photos/{index}`` — удалить фото.

Фото отдаются по адресу из ``images`` (``/api/media/...``).
"""

from datetime import UTC, datetime
from typing import NoReturn
from uuid import UUID

import structlog
from aiogram import Bot
from fastapi import APIRouter, HTTPException, Request, status

from bina.application.owner_listings import (
    LIMIT_REACHED,
    MAX_ACTIVE_LISTINGS,
    NO_CONTACT,
    NOT_FOUND,
    OwnerListingDraft,
    OwnerListingError,
    clean_phone,
    telegram_contact,
)
from bina.application.use_cases.owner_listings import OwnerListingsUseCase
from bina.infrastructure.api.dependencies import (
    CurrentUserDep,
    SessionDep,
    SettingsDep,
    TelegramUsernameDep,
)
from bina.infrastructure.api.routes.common import bad_request, not_found
from bina.infrastructure.api.routes.referral import bot_username
from bina.infrastructure.api.schemas import (
    MyListingOut,
    MyListingsOut,
    OwnerListingIn,
    OwnerListingPatchIn,
)
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.bot.owner_alerts import notify_admins
from bina.infrastructure.db.models import Listing, User
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository
from bina.infrastructure.storage.photos import MAX_PHOTO_BYTES, LocalPhotoStorage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/my/listings", tags=["my-listings"])


def _use_case(session: SessionDep) -> OwnerListingsUseCase:
    return OwnerListingsUseCase(OwnerListingsRepository(session), LocalPhotoStorage())


def _raise(error: OwnerListingError) -> NoReturn:
    if error.code == NOT_FOUND:
        raise not_found() from error
    if error.code == LIMIT_REACHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"At most {MAX_ACTIVE_LISTINGS} active listings: take one down first",
        ) from error
    if error.code == NO_CONTACT:
        raise bad_request("phone is required when you have no Telegram username") from error
    raise bad_request(error.code) from error


@router.get("", response_model=MyListingsOut)
async def list_my_listings(user: CurrentUserDep, session: SessionDep) -> MyListingsOut:
    """Свои объявления: активные сверху."""
    listings = await OwnerListingsRepository(session).list_for_user(user.id)
    return MyListingsOut(
        items=[MyListingOut.build(item) for item in listings], limit=MAX_ACTIVE_LISTINGS
    )


@router.post("", response_model=MyListingOut, status_code=status.HTTP_201_CREATED)
async def create_listing(
    request: Request,
    body: OwnerListingIn,
    user: CurrentUserDep,
    username: TelegramUsernameDep,
    session: SessionDep,
    settings: SettingsDep,
) -> MyListingOut:
    """Разместить квартиру (сразу в поиске). 409 — уже 5 активных объявлений."""
    phone = clean_phone(body.phone) if body.phone else None
    if body.phone and phone is None:
        raise bad_request("phone looks invalid")
    draft = OwnerListingDraft(
        city=body.city,
        district=body.district,
        rent_period=body.rent_period,
        price=body.price,
        currency=body.currency,
        rooms=body.rooms,
        area=body.area,
        description=body.description,
        floor=body.floor,
        total_floors=body.total_floors,
        phone=phone,
        contact_url=telegram_contact(username),
        features=body.features,
    )
    try:
        listing = await _use_case(session).publish(
            user.id,
            draft,
            [],
            datetime.now(UTC),
            bot_username=await _bot_username(request, settings),
        )
    except OwnerListingError as exc:
        _raise(exc)
    await session.commit()
    await _alert(settings, listing, user)
    return MyListingOut.build(listing)


async def _bot_username(request: Request, settings: ApiSettings) -> str | None:
    """Имя бота для кнопки «Написать» (чат через бота); бот не настроен — None."""
    try:
        return await bot_username(request, settings)
    except HTTPException:
        return None
    except Exception as exc:  # noqa: BLE001 - нет связи с Telegram: объявление всё равно разместим
        logger.warning("Bot username not resolved", error=str(exc))
        return None


@router.patch("/{listing_id}", response_model=MyListingOut)
async def update_listing(
    listing_id: UUID, body: OwnerListingPatchIn, user: CurrentUserDep, session: SessionDep
) -> MyListingOut:
    use_case = _use_case(session)
    now = datetime.now(UTC)
    try:
        listing = await use_case.owned(user.id, listing_id)
        if body.price is not None:
            currency = body.currency or listing.currency
            listing = await use_case.update_price(user.id, listing_id, body.price, currency, now)
        if body.active is not None:
            listing = await use_case.set_active(user.id, listing_id, body.active, now)
    except OwnerListingError as exc:
        _raise(exc)
    await session.commit()
    return MyListingOut.build(listing)


@router.post("/{listing_id}/photos", response_model=MyListingOut)
async def add_photo(
    listing_id: UUID, request: Request, user: CurrentUserDep, session: SessionDep
) -> MyListingOut:
    """Добавить фото: тело — файл картинки (JPEG, PNG, WebP, HEIC не поддерживается)."""
    data = await request.body()
    if not data or len(data) > MAX_PHOTO_BYTES:
        raise bad_request(f"photo must be 1 byte to {MAX_PHOTO_BYTES} bytes")
    try:
        listing = await _use_case(session).add_photo(user.id, listing_id, data)
    except OwnerListingError as exc:
        _raise(exc)
    await session.commit()
    return MyListingOut.build(listing)


@router.delete("/{listing_id}/photos/{index}", response_model=MyListingOut)
async def delete_photo(
    listing_id: UUID, index: int, user: CurrentUserDep, session: SessionDep
) -> MyListingOut:
    try:
        listing = await _use_case(session).delete_photo(user.id, listing_id, index)
    except OwnerListingError as exc:
        _raise(exc)
    await session.commit()
    return MyListingOut.build(listing)


async def _alert(settings: ApiSettings, listing: Listing, author: User) -> None:
    """Сообщение владельцу сервиса (без токена бота — пропускаем)."""
    if not settings.bot_token or not settings.admin_ids:
        return
    bot = Bot(token=settings.bot_token)
    try:
        await notify_admins(bot, settings.admin_ids, listing, author)
    finally:
        await bot.session.close()
