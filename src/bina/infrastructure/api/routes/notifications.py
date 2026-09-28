"""Уведомления текущего пользователя (TASK-028, FRONTEND-010)."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import MAX_PER_PAGE, not_found
from bina.infrastructure.api.schemas import (
    NotificationOut,
    NotificationsPageOut,
    UnreadCountOut,
)
from bina.infrastructure.db.repositories.notifications import NotificationsRepository

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsPageOut)
async def list_notifications(
    user: CurrentUserDep,
    session: SessionDep,
    filter: Annotated[Literal["all", "unread"], Query()] = "all",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=MAX_PER_PAGE)] = 20,
) -> NotificationsPageOut:
    """Уведомления (новые сверху), фильтр «все» или «непрочитанные»."""
    repository = NotificationsRepository(session)
    unread_only = filter == "unread"
    items = await repository.list_for_user(
        user.id, unread_only=unread_only, limit=per_page, offset=(page - 1) * per_page
    )
    total = await repository.count_for_user(user.id, unread_only=unread_only)
    unread = total if unread_only else await repository.count_for_user(user.id, unread_only=True)
    return NotificationsPageOut(
        items=[NotificationOut.from_model(item) for item in items],
        total=total,
        page=page,
        pages=max(1, -(-total // per_page)),
        unread_count=unread,
    )


@router.get("/unread-count", response_model=UnreadCountOut)
async def unread_count(user: CurrentUserDep, session: SessionDep) -> UnreadCountOut:
    """Число непрочитанных (бейдж колокольчика в шапке)."""
    count = await NotificationsRepository(session).count_for_user(user.id, unread_only=True)
    return UnreadCountOut(count=count)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all(user: CurrentUserDep, session: SessionDep) -> Response:
    """Отметить прочитанными все уведомления."""
    await NotificationsRepository(session).mark_all_read(user.id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_one(notification_id: UUID, user: CurrentUserDep, session: SessionDep) -> Response:
    """Отметить прочитанным; 404, если уведомления нет или оно чужое."""
    if not await NotificationsRepository(session).mark_read(user.id, notification_id):
        raise not_found("Notification not found")
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
