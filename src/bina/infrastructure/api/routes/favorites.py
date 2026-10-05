"""Избранное текущего пользователя.

Пользователь определяется по заголовку ``X-Telegram-Init-Data``
(см. :mod:`bina.infrastructure.api.auth`).
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel, Field

from bina.application.errors import LimitReachedError, ListingNotFoundError
from bina.application.subscriptions import limits_for
from bina.application.use_cases.favorites import (
    AddFavoriteUseCase,
    GetFavoritesUseCase,
    RemoveFavoriteUseCase,
)
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import MAX_PER_PAGE, not_found, payment_required
from bina.infrastructure.api.schemas import (
    FavoriteIdsOut,
    FavoriteIn,
    FavoriteOut,
    ListingsPageOut,
)
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository

router = APIRouter(prefix="/api/favorites", tags=["favorites"])

MAX_FAVORITE_IDS = 1000


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


@router.get("/ids", response_model=FavoriteIdsOut)
async def favorite_ids(user: CurrentUserDep, session: SessionDep) -> FavoriteIdsOut:
    """ID всех избранных объявлений (для отметок ♥ на карточках), последние добавленные сверху."""
    ids = await FavoritesRepository(session).list_ids(user.id, limit=MAX_FAVORITE_IDS)
    return FavoriteIdsOut(ids=ids)


@router.post("", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
async def add_favorite(body: FavoriteIn, user: CurrentUserDep, session: SessionDep) -> FavoriteOut:
    """Добавить объявление в избранное (повторный вызов ничего не меняет).

    402, если у тарифа есть лимит избранного и он заполнен (сейчас лимитов нет).
    """
    use_case = AddFavoriteUseCase(FavoritesRepository(session), ListingsRepository(session))
    limit = limits_for(user, datetime.now(UTC)).favorites
    try:
        await use_case.execute(user.id, body.listing_id, limit=limit)
    except ListingNotFoundError as exc:
        raise not_found() from exc
    except LimitReachedError as exc:
        raise payment_required(exc.kind, exc.limit) from exc
    await session.commit()
    return FavoriteOut(listing_id=body.listing_id)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(listing_id: UUID, user: CurrentUserDep, session: SessionDep) -> Response:
    """Убрать объявление из избранного (204, даже если его там не было)."""
    await RemoveFavoriteUseCase(FavoritesRepository(session)).execute(user.id, listing_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- TASK-074: заметки к избранному

MAX_NOTE = 300


class NotesOut(BaseModel):
    notes: dict[UUID, str] = Field(description="ID квартиры → заметка (только непустые)")


class NoteIn(BaseModel):
    note: str = Field(max_length=MAX_NOTE, description="Пустая строка — удалить заметку")


class NoteOut(BaseModel):
    listing_id: UUID
    note: str


@router.get("/notes", response_model=NotesOut)
async def favorite_notes(user: CurrentUserDep, session: SessionDep) -> NotesOut:
    """Свои заметки ко всему избранному."""
    return NotesOut(notes=await FavoritesRepository(session).notes(user.id))


@router.put("/{listing_id}/note", response_model=NoteOut)
async def set_favorite_note(
    listing_id: UUID, body: NoteIn, user: CurrentUserDep, session: SessionDep
) -> NoteOut:
    """Заметка к квартире в избранном; 404 — квартиры нет в избранном."""
    note = clean_text(body.note)
    if not await FavoritesRepository(session).set_note(user.id, listing_id, note):
        raise not_found("Listing is not in favorites")
    await session.commit()
    return NoteOut(listing_id=listing_id, note=note)
