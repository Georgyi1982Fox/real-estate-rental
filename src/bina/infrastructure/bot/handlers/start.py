from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.referrals import FRIEND_DISCOUNT_PERCENT, code_from_start
from bina.infrastructure.bot.keyboards.menu import main_menu
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.referrals import ReferralsRepository


async def cmd_start(
    message: Message,
    command: CommandObject,
    user: User,
    is_new_user: bool,
    session: AsyncSession,
) -> None:
    """/start: приветствие и главное меню; ``/start ref_<код>`` — приглашение друга (TASK-108)."""
    key = "welcome_new" if is_new_user else "welcome_back"
    await message.answer(t(user.language, key), reply_markup=main_menu(user.language))
    code = code_from_start(command.args)
    if code is None or not is_new_user:
        return
    referrals = ReferralsRepository(session)
    referrer = await referrals.by_code(code)
    if referrer is not None and await referrals.set_referrer(user, referrer):
        await message.answer(t(user.language, "welcome_referred", percent=FRIEND_DISCOUNT_PERCENT))


def create_router() -> Router:
    """Создаёт роутер раздела «start» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="start")
    router.message.register(cmd_start, CommandStart())
    return router
