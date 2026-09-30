"""Роутеры обработчиков бота."""

from aiogram import Router

from . import errors, fallback, favorites, help, invite, payments, profile, rent, search, start


def build_router() -> Router:
    """Корневой роутер. Порядок важен: ``fallback`` подключается последним.

    Каждый вызов создаёт новые роутеры, поэтому можно собрать несколько
    Dispatcher в одном процессе (тесты, повторный запуск).
    """
    router = Router(name="bina")
    router.include_routers(
        errors.create_router(),
        start.create_router(),
        help.create_router(),
        search.create_router(),
        favorites.create_router(),
        profile.create_router(),
        payments.create_router(),
        invite.create_router(),
        rent.create_router(),
        fallback.create_router(),
    )
    return router
