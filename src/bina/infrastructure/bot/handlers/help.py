from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bina.infrastructure.bot.texts import t
from src.bina.infrastructure.db.models import User


async def cmd_help(message: Message, user: User) -> None:
    """/help: список команд."""
    await message.answer(t(user.language, "help"))


def create_router() -> Router:
    """Создаёт роутер раздела «help» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="help")
    router.message.register(cmd_help, Command("help"))
    return router
