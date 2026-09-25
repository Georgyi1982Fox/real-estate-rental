"""Запуск бота в режимах polling и webhook."""

import structlog
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from src.bina.infrastructure.bot.factory import create_bot, create_dispatcher, setup_bot_ui
from src.bina.infrastructure.bot.settings import BotSettings
from src.bina.infrastructure.db.session.manager import DatabaseManager

logger = structlog.get_logger(__name__)

HEALTH_PATH = "/health"


async def run_polling(settings: BotSettings) -> None:
    """Запускает long polling до остановки процесса (Ctrl+C / SIGTERM).

    Снимает ранее установленный вебхук: Telegram не отдаёт апдейты через
    getUpdates, пока вебхук активен.
    """
    db = DatabaseManager()
    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings, db.session_factory)
    try:
        await bot.delete_webhook(drop_pending_updates=settings.drop_pending_updates)
        await setup_bot_ui(bot, settings)
        logger.info("Bot polling started")
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()
        await db.dispose()
        logger.info("Bot polling stopped")


def build_webhook_app(
    bot: Bot,
    dispatcher: Dispatcher,
    settings: BotSettings,
) -> web.Application:
    """aiohttp-приложение: ``POST <webhook_path>`` для Telegram и ``GET /health``.

    При старте регистрирует вебхук в Telegram, при остановке закрывает сессию бота.
    """

    async def on_startup(bot: Bot) -> None:
        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.webhook_secret,
            allowed_updates=dispatcher.resolve_used_update_types(),
            drop_pending_updates=settings.drop_pending_updates,
        )
        await setup_bot_ui(bot, settings)
        logger.info("Webhook set", url=settings.webhook_url)

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    dispatcher.startup.register(on_startup)

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.webhook_secret,
    ).register(app, path=settings.webhook_path)
    app.router.add_get(HEALTH_PATH, health)
    setup_application(app, dispatcher, bot=bot)
    return app


def run_webhook(settings: BotSettings) -> None:
    """Запускает aiohttp-сервер для вебхука (блокирующий вызов).

    TLS обычно терминирует обратный прокси (nginx, Caddy), который
    проксирует ``BOT_WEBHOOK_BASE_URL`` на ``BOT_WEBAPP_HOST:BOT_WEBAPP_PORT``.
    """
    if not settings.webhook_secret:
        logger.warning("BOT_WEBHOOK_SECRET is not set: webhook requests are not authenticated")

    db = DatabaseManager()
    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings, db.session_factory)

    async def dispose_db() -> None:
        await db.dispose()

    dispatcher.shutdown.register(dispose_db)
    app = build_webhook_app(bot, dispatcher, settings)
    web.run_app(app, host=settings.webapp_host, port=settings.webapp_port, print=None)
