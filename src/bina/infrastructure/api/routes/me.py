"""Профиль текущего пользователя (страница «Профиль» Mini App).

Пользователь определяется по заголовку ``X-Telegram-Init-Data``
(см. :mod:`bina.infrastructure.api.auth`), отдельный токен (JWT) не нужен.
"""

from fastapi import APIRouter

from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.schemas import MeIn, MeOut
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.users import UsersRepository

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=MeOut)
async def get_me(user: CurrentUserDep, session: SessionDep) -> MeOut:
    """Язык, подписка, баланс, число избранных, дата регистрации."""
    favorites_count = await FavoritesRepository(session).count_by_user(user.id)
    return MeOut.from_model(user, favorites_count)


@router.patch("", response_model=MeOut)
async def update_me(body: MeIn, user: CurrentUserDep, session: SessionDep) -> MeOut:
    """Сменить язык интерфейса (``ru``, ``en``, ``ka``)."""
    await UsersRepository(session).update_language(user.id, body.language)
    await session.commit()
    user.language = body.language
    favorites_count = await FavoritesRepository(session).count_by_user(user.id)
    return MeOut.from_model(user, favorites_count)
