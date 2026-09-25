"""Сборка Bot и Dispatcher."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bina.infrastructure.bot.handlers import build_router
from src.bina.infrastructure.bot.middlewares import DbSessionMiddleware, RegistrationMiddleware
from src.bina.infrastructure.bot.settings import BotSettings
from src.bina.infrastructure.bot.texts import t

COMMANDS: dict[str, dict[str, str]] = {
    "ru": {
        "search": "Поиск жилья",
        "favorites": "Избранное",
        "profile": "Профиль и язык",
        "help": "Справка",
    },
    "en": {
        "search": "Find a home",
        "favorites": "Favorites",
        "profile": "Profile and language",
        "help": "Help",
    },
}
DEFAULT_COMMANDS_LANGUAGE = "ru"


def create_bot(settings: BotSettings) -> Bot:
    """Создаёт Bot с HTML-разметкой по умолчанию."""
    return Bot(
        token=settings.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(
    settings: BotSettings,
    session_factory: async_sessionmaker[AsyncSession],
) -> Dispatcher:
    """Создаёт Dispatcher с middleware и роутерами.

    ``settings`` доступны в обработчиках как аргумент ``settings``.
    Порядок middleware: сессия БД, затем регистрация (ей нужна сессия).
    """
    dispatcher = Dispatcher(settings=settings)
    dispatcher.update.outer_middleware(DbSessionMiddleware(session_factory))
    dispatcher.update.outer_middleware(RegistrationMiddleware())
    dispatcher.include_router(build_router())
    return dispatcher


async def setup_bot_ui(bot: Bot, settings: BotSettings) -> None:
    """Регистрирует команды в меню Telegram и кнопку Mini App (если задан URL)."""
    for language, commands in COMMANDS.items():
        await bot.set_my_commands(
            [BotCommand(command=name, description=text) for name, text in commands.items()],
            language_code=None if language == DEFAULT_COMMANDS_LANGUAGE else language,
        )
    if settings.mini_app_url:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text=t(DEFAULT_COMMANDS_LANGUAGE, "open_app"),
                web_app=WebAppInfo(url=settings.mini_app_url),
            )
        )
