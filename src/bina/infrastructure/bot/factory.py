"""Сборка Bot и Dispatcher."""

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand, BotCommandScopeChat, MenuButtonWebApp, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.embeddings import IEmbedder
from bina.infrastructure.bot.handlers import build_router
from bina.infrastructure.bot.middlewares import DbSessionMiddleware, RegistrationMiddleware
from bina.infrastructure.bot.middlewares.throttling import ThrottlingMiddleware
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import t
from bina.infrastructure.payments.settings import load_plans

COMMANDS: dict[str, dict[str, str]] = {
    "ru": {
        "search": "Поиск жилья",
        "favorites": "Избранное",
        "profile": "Профиль и язык",
        "premium": "Premium-подписка",
        "invite": "Пригласить друга",
        "rent": "Напоминания об оплате аренды",
        "terms": "Пользовательское соглашение",
        "privacy": "Конфиденциальность",
        "paysupport": "Поддержка и вопросы по оплате",
        "help": "Справка",
    },
    "en": {
        "search": "Find a home",
        "favorites": "Favorites",
        "profile": "Profile and language",
        "premium": "Premium subscription",
        "invite": "Invite a friend",
        "rent": "Rent payment reminders",
        "terms": "Terms of use",
        "privacy": "Privacy policy",
        "paysupport": "Support and payment questions",
        "help": "Help",
    },
    "ka": {
        "search": "ბინის ძებნა",
        "favorites": "რჩეულები",
        "profile": "პროფილი და ენა",
        "premium": "Premium გამოწერა",
        "invite": "მეგობრის მოწვევა",
        "rent": "ქირის გადახდის შეხსენებები",
        "terms": "სამომხმარებლო შეთანხმება",
        "privacy": "კონფიდენციალურობა",
        "paysupport": "მხარდაჭერა და გადახდის კითხვები",
        "help": "დახმარება",
    },
}
DEFAULT_COMMANDS_LANGUAGE = "ru"
ADMIN_COMMAND = {"admin": "Админка: статистика и жалобы"}

logger = structlog.get_logger(__name__)


def create_bot(settings: BotSettings) -> Bot:
    """Создаёт Bot с HTML-разметкой по умолчанию."""
    return Bot(
        token=settings.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(
    settings: BotSettings,
    session_factory: async_sessionmaker[AsyncSession],
    embedder: IEmbedder | None = None,
) -> Dispatcher:
    """Создаёт Dispatcher с middleware и роутерами.

    ``settings`` и тарифы ``plans`` доступны в обработчиках как одноимённые аргументы.
    Порядок middleware: сессия БД, затем регистрация (ей нужна сессия).
    """
    # embedder — умный поиск по тексту сообщения (TASK-012); None — выключен
    dispatcher = Dispatcher(settings=settings, plans=load_plans(), embedder=embedder)
    # Флуд отбрасывается до обращения к базе (TASK-019)
    dispatcher.update.outer_middleware(ThrottlingMiddleware(settings.rate_limit))
    dispatcher.update.outer_middleware(DbSessionMiddleware(session_factory))
    dispatcher.update.outer_middleware(RegistrationMiddleware())
    dispatcher.include_router(build_router())
    return dispatcher


async def setup_bot_ui(bot: Bot, settings: BotSettings) -> None:
    """Регистрирует команды в меню Telegram и кнопку Mini App (если задан URL).

    Владельцу (``ADMIN_TELEGRAM_IDS``) в его чате видна ещё и ``/admin`` (TASK-110).
    """
    for language, commands in COMMANDS.items():
        await bot.set_my_commands(
            [BotCommand(command=name, description=text) for name, text in commands.items()],
            language_code=None if language == DEFAULT_COMMANDS_LANGUAGE else language,
        )
    admin_commands = [
        BotCommand(command=name, description=text)
        for name, text in {**COMMANDS[DEFAULT_COMMANDS_LANGUAGE], **ADMIN_COMMAND}.items()
    ]
    for admin_id in settings.admin_ids:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except TelegramBadRequest as exc:
            # Владелец ещё не писал боту — меню появится после перезапуска бота
            logger.warning("Admin commands not set", admin_id=admin_id, error=str(exc))
    if settings.mini_app_url:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text=t(DEFAULT_COMMANDS_LANGUAGE, "open_app"),
                web_app=WebAppInfo(url=settings.mini_app_url),
            )
        )
