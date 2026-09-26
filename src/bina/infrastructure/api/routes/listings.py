"""Объявления: список с фильтрами, карточка, похожие."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import ValidationError

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.use_cases.search_listings import SearchListingsUseCase
from bina.infrastructure.api.dependencies import SessionDep
from bina.infrastructure.api.routes.common import (
    MAX_PER_PAGE,
    bad_request,
    get_listing_or_404,
    parse_decimal,
    parse_uuid,
)
from bina.infrastructure.api.schemas import ListingOut, ListingsOut, ListingsPageOut
from bina.infrastructure.db.repositories.listings import ListingsRepository

router = APIRouter(prefix="/api/listings", tags=["listings"])

# «4» в фильтре фронтенда означает «4 и больше»
ROOMS_OR_MORE = 4
SIMILAR_LIMIT = 3
SIMILAR_PRICE_SPREAD = Decimal("0.3")


@router.get("", response_model=ListingsPageOut)
async def list_listings(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=MAX_PER_PAGE)] = 20,
    district: Annotated[str | None, Query(description="ID района")] = None,
    min_price: Annotated[str | None, Query()] = None,
    max_price: Annotated[str | None, Query()] = None,
    rooms: Annotated[int | None, Query(ge=1, description="4 = «4 и больше»")] = None,
) -> ListingsPageOut:
    """Активные объявления, новые сверху, с пагинацией и фильтрами."""
    try:
        filters = ListingSearchFilters(
            district_id=parse_uuid(district, "district"),
            price_min=parse_decimal(min_price, "min_price"),
            price_max=parse_decimal(max_price, "max_price"),
            rooms_min=rooms,
            rooms_max=None if rooms is None or rooms >= ROOMS_OR_MORE else rooms,
        )
    except ValidationError as exc:
        raise bad_request("min_price must be <= max_price") from exc

    result = await SearchListingsUseCase(ListingsRepository(session)).execute(
        filters, page=page - 1, page_size=per_page
    )
    return ListingsPageOut.from_page(result)


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(listing_id: str, session: SessionDep) -> ListingOut:
    """Одно объявление; 404, если его нет или оно удалено."""
    return ListingOut.from_model(await get_listing_or_404(session, listing_id))


@router.get("/{listing_id}/similar", response_model=ListingsOut)
async def similar_listings(listing_id: str, session: SessionDep) -> ListingsOut:
    """До трёх активных объявлений того же района с ценой ±30%."""
    listing = await get_listing_or_404(session, listing_id)
    filters = ListingSearchFilters(
        district_id=listing.district_id,
        price_min=listing.price * (1 - SIMILAR_PRICE_SPREAD),
        price_max=listing.price * (1 + SIMILAR_PRICE_SPREAD),
    )
    candidates = await ListingsRepository(session).search(filters, limit=SIMILAR_LIMIT + 1)
    items = [item for item in candidates if item.id != listing.id][:SIMILAR_LIMIT]
    return ListingsOut(items=[ListingOut.from_model(item) for item in items])
