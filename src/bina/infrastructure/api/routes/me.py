"""Профиль текущего пользователя (страница «Профиль» Mini App).

Пользователь определяется по заголовку ``X-Telegram-Init-Data``
(см. :mod:`bina.infrastructure.api.auth`), отдельный токен (JWT) не нужен.
"""

from fastapi import APIRouter

from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep, SettingsDep
from bina.infrastructure.api.schemas import MeIn, MeOut
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import UserRole
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.users import UsersRepository

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


def is_admin(user: User, settings: ApiSettings) -> bool:
    """Владелец: Telegram ID из ``ADMIN_TELEGRAM_IDS`` или роль admin."""
    return user.telegram_id in settings.admin_ids or user.role == UserRole.ADMIN
