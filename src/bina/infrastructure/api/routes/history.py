"""«Недавно смотрели» (TASK-075): ``GET /api/history`` и ``DELETE /api/history``.

Просмотр записывается, когда вошедший пользователь открывает квартиру
(``GET /api/listings/{id}``) или карточку в боте.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel

from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.schemas import ListingOut
from bina.infrastructure.db.repositories.view_history import ViewHistoryRepository

router = APIRouter(prefix="/api/history", tags=["history"])


class ViewedOut(BaseModel):
    listing: ListingOut
    viewed_at: datetime


class HistoryOut(BaseModel):
    items: list[ViewedOut]


@router.get("", response_model=HistoryOut)
async def history(
    user: CurrentUserDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> HistoryOut:
    """Недавно смотренные квартиры, новые сверху."""
    rows = await ViewHistoryRepository(session).recent(user.id, limit)
    return HistoryOut(
        items=[ViewedOut(listing=ListingOut.from_model(item), viewed_at=at) for item, at in rows]
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(user: CurrentUserDep, session: SessionDep) -> Response:
    """Очистить «Недавно смотрели»."""
    await ViewHistoryRepository(session).clear(user.id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
