from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.bina.infrastructure.bot.keyboards.menu import main_menu
from src.bina.infrastructure.bot.texts import t
from src.bina.infrastructure.db.models import User


async def cmd_start(message: Message, user: User, is_new_user: bool) -> None:
    """/start: приветствие и главное меню."""
    key = "welcome_new" if is_new_user else "welcome_back"
    await message.answer(t(user.language, key), reply_markup=main_menu(user.language))


def create_router() -> Router:
    """Создаёт роутер раздела «start» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="start")
    router.message.register(cmd_start, CommandStart())
    return router
