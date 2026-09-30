"""FastAPI-приложение Bina.ai и команда запуска ``bina-api``.

Запуск: ``bina-api --host 0.0.0.0 --port 8000``
или ``uvicorn bina.infrastructure.api.server:app``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import click
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.api.auth import INIT_DATA_HEADER
from bina.infrastructure.api.errors import REQUEST_ID_HEADER, install_error_handling
from bina.infrastructure.api.routes import (
    acceptance,
    assistant,
    compare,
    complaints,
    contract,
    costs,
    districts,
    favorites,
    listings,
    location,
    me,
    notifications,
    referral,
    searches,
    subscription,
)
from bina.infrastructure.api.settings import ApiConfigError, ApiSettings
from bina.infrastructure.api.validation import install_body_limit
from bina.infrastructure.db.session.manager import DatabaseManager
from bina.infrastructure.payments.settings import load_plans


def create_app(
    settings: ApiSettings | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    """Создаёт приложение.

    Без ``session_factory`` подключается к ``DATABASE_URL`` через
    :class:`DatabaseManager` (пул закрывается при остановке).
    """
    settings = settings or ApiSettings.from_env()
    db = DatabaseManager() if session_factory is None else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if db is not None:
            await db.dispose()

    app = FastAPI(title="Bina.ai API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = session_factory or (db.session_factory if db else None)
    app.state.plans = load_plans()

    # Порядок важен: последний добавленный middleware — внешний. CORS снаружи,
    # чтобы заголовки попали и в ответы с ошибками (413, 500)
    install_body_limit(app)
    install_error_handling(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", INIT_DATA_HEADER, REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )

    @app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Проверка, что сервер жив (без обращения к БД)."""
        return {"status": "ok"}

    # До listings: иначе «compare» примется за ID объявления
    app.include_router(compare.router)
    app.include_router(listings.router)
    app.include_router(assistant.router)
    app.include_router(contract.router)
    app.include_router(acceptance.router)
    app.include_router(costs.router)
    app.include_router(complaints.router)
    app.include_router(location.router)
    app.include_router(districts.router)
    app.include_router(favorites.router)
    app.include_router(me.router)
    app.include_router(searches.router)
    app.include_router(notifications.router)
    app.include_router(subscription.router)
    app.include_router(referral.router)
    return app


app = create_app()


@click.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Адрес сервера.")
@click.option("--port", default=8000, show_default=True, type=int, help="Порт сервера.")
@click.option("--reload", is_flag=True, help="Перезапуск при изменении кода (разработка).")
def cli(host: str, port: int, reload: bool) -> None:
    """Запуск REST API Bina.ai (FastAPI + uvicorn).

    Настройки: DATABASE_URL, BOT_TOKEN, API_CORS_ORIGINS, API_ALLOW_INSECURE_USER_ID.
    """
    try:
        ApiSettings.from_env()
    except ApiConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    uvicorn.run("bina.infrastructure.api.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    cli()
