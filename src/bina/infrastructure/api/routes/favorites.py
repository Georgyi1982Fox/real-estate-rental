"""Избранное текущего пользователя.

Пользователь определяется по заголовку ``X-Telegram-Init-Data``
(см. :mod:`bina.infrastructure.api.auth`).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from bina.application.errors import ListingNotFoundError
from bina.application.use_cases.favorites import (
    AddFavoriteUseCase,
    GetFavoritesUseCase,
    RemoveFavoriteUseCase,
)
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import MAX_PER_PAGE, not_found
from bina.infrastructure.api.schemas import FavoriteIn, FavoriteOut, ListingsPageOut
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("", response_model=ListingsPageOut)
async def list_favorites(
    user: CurrentUserDep,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=MAX_PER_PAGE)] = 20,
) -> ListingsPageOut:
    """Избранные объявления (последние добавленные сверху)."""
    result = await GetFavoritesUseCase(FavoritesRepository(session)).execute(
        user.id, page=page - 1, page_size=per_page
    )
    return ListingsPageOut.from_page(result)


@router.post("", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
async def add_favorite(body: FavoriteIn, user: CurrentUserDep, session: SessionDep) -> FavoriteOut:
    """Добавить объявление в избранное (повторный вызов ничего не меняет)."""
    use_case = AddFavoriteUseCase(FavoritesRepository(session), ListingsRepository(session))
    try:
        await use_case.execute(user.id, body.listing_id)
    except ListingNotFoundError as exc:
        raise not_found() from exc
    await session.commit()
    return FavoriteOut(listing_id=body.listing_id)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(listing_id: UUID, user: CurrentUserDep, session: SessionDep) -> Response:
    """Убрать объявление из избранного (204, даже если его там не было)."""
    await RemoveFavoriteUseCase(FavoritesRepository(session)).execute(user.id, listing_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
