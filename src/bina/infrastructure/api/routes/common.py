"""Общие помощники маршрутов."""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.cities import CITIES
from bina.infrastructure.db.models import Listing, ListingStatus
from bina.infrastructure.db.repositories.listings import ListingsRepository

MAX_PER_PAGE = 50


def not_found(detail: str = "Listing not found") -> HTTPException:
    """Ошибка 404."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def bad_request(detail: str) -> HTTPException:
    """Ошибка 422 с понятным сообщением."""
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def payment_required(kind: str, limit: int) -> HTTPException:
    """Ошибка 402: лимит бесплатного тарифа исчерпан, нужен Premium (TASK-026)."""
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=f"Free plan limit reached: {kind} ({limit}). Upgrade to Premium",
    )


def parse_uuid(value: str | None, name: str) -> UUID | None:
    """UUID из query-параметра; пустая строка означает «не задано»."""
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise bad_request(f"{name} must be a UUID") from exc


MAX_DISTRICTS = 20


def parse_districts(values: list[str] | None) -> list[UUID]:
    """Районы из ``district``: повтором параметра или через запятую; пустые — не заданы."""
    parts = [part.strip() for value in values or [] for part in value.split(",")]
    ids = list(dict.fromkeys(uuid for part in parts if (uuid := parse_uuid(part, "district"))))
    if len(ids) > MAX_DISTRICTS:
        raise bad_request(f"At most {MAX_DISTRICTS} districts")
    return ids


def parse_codes(value: str | None, allowed: tuple[str, ...], name: str) -> tuple[str, ...]:
    """Коды через запятую (``furniture,elevator``); неизвестный код — 422."""
    codes = tuple(dict.fromkeys(part.strip() for part in (value or "").split(",") if part.strip()))
    unknown = [code for code in codes if code not in allowed]
    if unknown:
        raise bad_request(f"unknown {name}: {', '.join(unknown)}")
    return codes


def parse_decimal(value: str | None, name: str) -> Decimal | None:
    """Число из query-параметра; пустая строка означает «не задано»."""
    if not value:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise bad_request(f"{name} must be a number") from exc
    if not number.is_finite() or number < 0:
        raise bad_request(f"{name} must be a non-negative number")
    return number


async def get_listing_or_404(session: AsyncSession, listing_id: str) -> Listing:
    """Объявление по ID из пути; 404, если ID некорректен, объявления нет или оно удалено."""
    try:
        uuid = UUID(listing_id)
    except ValueError as exc:
        raise not_found() from exc
    listing = await ListingsRepository(session).get_by_id(uuid)
    if listing is None or listing.is_deleted:
        raise not_found()
    return listing


async def get_visible_listing_or_404(session: AsyncSession, listing_id: str) -> Listing:
    """Объявление в поиске: не снято, не скрыто модератором или блокировкой агентства.

    Для контактов (телефон, «Написать»): по старой ссылке скрытое объявление открыть можно,
    а связаться — нет.
    """
    listing = await get_listing_or_404(session, listing_id)
    if listing.status != ListingStatus.ACTIVE or listing.hidden_at is not None:
        raise not_found()
    return listing


def valid_city(city: str | None) -> str | None:
    """Проверить код города (TASK-079); неизвестный — 400 с понятным сообщением."""
    if city is not None and city not in CITIES:
        raise bad_request(f"unknown city: {city}")
    return city
