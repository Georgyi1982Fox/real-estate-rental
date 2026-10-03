"""Профиль текущего пользователя (страница «Профиль» Mini App).

``GET /api/me/export`` — все свои данные файлом, ``DELETE /api/me?confirm=true`` — удалить
аккаунт и данные (TASK-059, TASK-060).

Пользователь определяется по заголовку ``X-Telegram-Init-Data``
(см. :mod:`bina.infrastructure.api.auth`), отдельный токен (JWT) не нужен.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse

from bina.application.use_cases.account import AccountUseCase
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep, SettingsDep
from bina.infrastructure.api.schemas import MeIn, MeOut
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import UserRole
from bina.infrastructure.db.repositories.account import AccountRepository
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from bina.infrastructure.storage.photos import LocalPhotoStorage

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=MeOut)
async def get_me(user: CurrentUserDep, session: SessionDep, settings: SettingsDep) -> MeOut:
    """Язык, подписка, баланс, число избранных, дата регистрации, владелец ли."""
    favorites_count = await FavoritesRepository(session).count_by_user(user.id)
    return MeOut.from_model(user, favorites_count, is_admin(user, settings))


@router.patch("", response_model=MeOut)
async def update_me(
    body: MeIn, user: CurrentUserDep, session: SessionDep, settings: SettingsDep
) -> MeOut:
    """Сменить язык интерфейса (``ru``, ``en``, ``ka``)."""
    await UsersRepository(session).update_language(user.id, body.language)
    await session.commit()
    user.language = body.language
    favorites_count = await FavoritesRepository(session).count_by_user(user.id)
    return MeOut.from_model(user, favorites_count, is_admin(user, settings))


@router.get("/export")
async def export_me(user: CurrentUserDep, session: SessionDep) -> JSONResponse:
    """Все свои данные одним JSON-файлом (TASK-059)."""
    use_case = AccountUseCase(AccountRepository(session), LocalPhotoStorage())
    data = await use_case.export(user, datetime.now(UTC))
    return JSONResponse(
        data,
        headers={"Content-Disposition": 'attachment; filename="bina-my-data.json"'},
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: CurrentUserDep,
    session: SessionDep,
    confirm: bool = Query(default=False, description="true — да, удалить всё без возврата"),
) -> Response:
    """Удалить аккаунт и все свои данные (TASK-060). Без ``confirm=true`` — 400."""
    if not confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pass confirm=true to delete everything")
    use_case = AccountUseCase(AccountRepository(session), LocalPhotoStorage())
    await use_case.erase(user, datetime.now(UTC), session.commit)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def is_admin(user: User, settings: ApiSettings) -> bool:
    """Владелец: Telegram ID из ``ADMIN_TELEGRAM_IDS`` или роль admin."""
    return user.telegram_id in settings.admin_ids or user.role == UserRole.ADMIN
