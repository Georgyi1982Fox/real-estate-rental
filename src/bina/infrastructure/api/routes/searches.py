"""Сохранённые поиски текущего пользователя (TASK-028, FRONTEND-009).

Пользователь определяется по заголовку ``X-Telegram-Init-Data``.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Response, status

from bina.application.dtos.listing_search import ROOMS_OR_MORE, search_filters
from bina.application.subscriptions import limits_for
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import bad_request, not_found, payment_required
from bina.infrastructure.api.schemas import (
    SavedSearchesOut,
    SavedSearchOut,
    SearchFiltersIn,
    SearchIn,
    SearchPatchIn,
)
from bina.infrastructure.db.models import District, SavedSearch
from bina.infrastructure.db.repositories.districts import DistrictsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.notifications import SavedSearchesRepository

router = APIRouter(prefix="/api/searches", tags=["searches"])

# Короткое тире в диапазоне цен
DASH = "\u2013"

_NAME_PARTS: dict[str, dict[str, str]] = {
    "ru": {"all": "Все квартиры", "rooms": "{n} комн.", "from": "от {n} ₾", "to": "до {n} ₾"},
    "en": {
        "all": "All apartments",
        "rooms": "{n} rooms",
        "from": "from {n} ₾",
        "to": "up to {n} ₾",
    },
    "ka": {"all": "ყველა ბინა", "rooms": "{n} ოთახი", "from": "{n} ₾-დან", "to": "{n} ₾-მდე"},
}


def _amount(value: Decimal) -> str:
    return f"{int(value):,}".replace(",", " ")


def default_search_name(filters: SearchFiltersIn, district: District | None, language: str) -> str:
    """Название из фильтров: «Ваке, 2 комн., 800-2000 ₾» (через короткое тире)."""
    parts = _NAME_PARTS.get(language, _NAME_PARTS["ru"])
    result: list[str] = []
    if district is not None:
        localized_names = {"ru": district.name_ru, "en": district.name_en, "ka": district.name_ka}
        district_name = localized_names.get(language) or district.name_ru
        if district_name:
            result.append(district_name)
    if filters.rooms is not None:
        rooms = f"{ROOMS_OR_MORE}+" if filters.rooms >= ROOMS_OR_MORE else str(filters.rooms)
        result.append(parts["rooms"].format(n=rooms))
    if filters.min_price is not None and filters.max_price is not None:
        result.append(f"{_amount(filters.min_price)}{DASH}{_amount(filters.max_price)} ₾")
    elif filters.min_price is not None:
        result.append(parts["from"].format(n=_amount(filters.min_price)))
    elif filters.max_price is not None:
        result.append(parts["to"].format(n=_amount(filters.max_price)))
    return ", ".join(result) or parts["all"]


async def _search_out(session: SessionDep, search: SavedSearch) -> SavedSearchOut:
    filters = search_filters(
        district_id=search.district_id,
        price_min=search.price_min,
        price_max=search.price_max,
        rooms=search.rooms,
    )
    new_count = await ListingsRepository(session).count_created_since(
        filters, search.last_viewed_at
    )
    return SavedSearchOut.from_model(search, new_count)


async def _get_or_404(session: SessionDep, user_id: UUID, search_id: UUID) -> SavedSearch:
    search = await SavedSearchesRepository(session).get(user_id, search_id)
    if search is None:
        raise not_found("Search not found")
    return search


@router.get("", response_model=SavedSearchesOut)
async def list_searches(user: CurrentUserDep, session: SessionDep) -> SavedSearchesOut:
    """Поиски пользователя (новые сверху) с числом новых квартир."""
    searches = await SavedSearchesRepository(session).list_by_user(user.id)
    return SavedSearchesOut(items=[await _search_out(session, item) for item in searches])


@router.post("", response_model=SavedSearchOut, status_code=status.HTTP_201_CREATED)
async def create_search(
    body: SearchIn, user: CurrentUserDep, session: SessionDep
) -> SavedSearchOut:
    """Сохранить поиск; без ``name`` название собирается из фильтров.

    402, если поисков уже столько, сколько позволяет тариф (бесплатно 1, Premium 20).
    """
    repository = SavedSearchesRepository(session)
    limit = limits_for(user, datetime.now(UTC)).searches
    if await repository.count_by_user(user.id) >= limit:
        raise payment_required("searches", limit)
    filters = body.filters
    district = None
    if filters.district is not None:
        district = await DistrictsRepository(session).get_by_id(filters.district)
        if district is None:
            raise bad_request("district not found")
    name = (body.name or "").strip() or default_search_name(filters, district, user.language)
    search = await repository.create(
        user.id,
        name=name,
        district_id=filters.district,
        price_min=filters.min_price,
        price_max=filters.max_price,
        rooms=filters.rooms,
        notify=body.notify,
    )
    await session.commit()
    return await _search_out(session, search)


@router.patch("/{search_id}", response_model=SavedSearchOut)
async def update_search(
    search_id: UUID, body: SearchPatchIn, user: CurrentUserDep, session: SessionDep
) -> SavedSearchOut:
    """Переименовать поиск или включить/выключить уведомления."""
    search = await _get_or_404(session, user.id, search_id)
    if body.name is not None:
        search.name = body.name.strip() or search.name
    if body.notify is not None:
        if body.notify and not search.notify:
            # Без уведомлений о квартирах, появившихся, пока они были выключены
            search.notify_since = datetime.now(UTC)
        search.notify = body.notify
    await session.commit()
    await session.refresh(search)
    return await _search_out(session, search)


@router.post("/{search_id}/viewed", status_code=status.HTTP_204_NO_CONTENT)
async def mark_viewed(search_id: UUID, user: CurrentUserDep, session: SessionDep) -> Response:
    """Пользователь открыл поиск: счётчик новых квартир обнуляется."""
    search = await _get_or_404(session, user.id, search_id)
    search.last_viewed_at = datetime.now(UTC)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search(search_id: UUID, user: CurrentUserDep, session: SessionDep) -> Response:
    """Удалить поиск (204, даже если его не было)."""
    await SavedSearchesRepository(session).delete(user.id, search_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
