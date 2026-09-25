from aiogram import Router
from aiogram.types import Message

from src.bina.infrastructure.bot.texts import t
from src.bina.infrastructure.db.models import User


async def on_unknown_message(message: Message, user: User) -> None:
    """Любое нераспознанное сообщение: подсказка про меню и /help."""
    await message.answer(t(user.language, "unknown"))


def create_router() -> Router:
    """Создаёт роутер раздела «fallback» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="fallback")
    router.message.register(on_unknown_message)
    return router
