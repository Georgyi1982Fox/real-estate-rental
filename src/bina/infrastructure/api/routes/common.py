"""Общие помощники маршрутов."""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository

MAX_PER_PAGE = 50


def not_found(detail: str = "Listing not found") -> HTTPException:
    """Ошибка 404."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def bad_request(detail: str) -> HTTPException:
    """Ошибка 422 с понятным сообщением."""
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def parse_uuid(value: str | None, name: str) -> UUID | None:
    """UUID из query-параметра; пустая строка означает «не задано»."""
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise bad_request(f"{name} must be a UUID") from exc


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
