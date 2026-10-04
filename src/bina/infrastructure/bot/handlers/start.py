from uuid import UUID

from aiogram import Bot, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.chat import listing_from_start
from bina.application.ports.embeddings import IEmbedder
from bina.application.referrals import FRIEND_DISCOUNT_PERCENT, code_from_start
from bina.application.sharing import listing_from_share
from bina.application.subscriptions import Plan
from bina.infrastructure.bot.handlers import chat, listing_card, menu
from bina.infrastructure.bot.keyboards.menu import main_menu
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.referrals import ReferralsRepository


async def cmd_start(
    message: Message,
    command: CommandObject,
    user: User,
    is_new_user: bool,
    session: AsyncSession,
    settings: BotSettings,
    plans: dict[str, Plan],
    bot: Bot,
    state: FSMContext,
    embedder: IEmbedder | None = None,
) -> None:
    """/start: приветствие и главное меню.

    ``/start ref_<код>`` — приглашение друга (TASK-108); ``/start rent``, ``/start support`` …
    — сразу раздел меню (кнопки сайта, FRONTEND-034); ``/start chat_<id>`` — написать
    хозяину квартиры (TASK-111); ``/start l_<id>`` — квартира, которой поделились (TASK-073).
    """
    key = "welcome_new" if is_new_user else "welcome_back"
    await message.answer(t(user.language, key), reply_markup=main_menu(user.language))
    code = code_from_start(command.args)
    if code is not None and is_new_user:
        referrals = ReferralsRepository(session)
        referrer = await referrals.by_code(code)
        if referrer is not None and await referrals.set_referrer(user, referrer):
            await message.answer(
                t(user.language, "welcome_referred", percent=FRIEND_DISCOUNT_PERCENT)
            )
    if (listing_id := _listing_id(command.args)) is not None:
        await chat.show_listing(message, user, session, listing_id)
        return
    # TASK-073: ссылка «Поделиться квартирой»
    if (shared := listing_from_share(command.args)) is not None:
        await listing_card.show_card(message, user, session, settings, bot, shared)
        return
    section = menu.section_from_start(command.args)
    if section is None:
        await menu.send_home(message, user, settings)
        return
    await menu.open_section(
        message,
        section,
        user=user,
        session=session,
        settings=settings,
        plans=plans,
        bot=bot,
        state=state,
        embedder=embedder,
    )


def _listing_id(payload: str | None) -> UUID | None:
    value = listing_from_start(payload)
    try:
        return UUID(value) if value else None
    except ValueError:
        return None


def create_router() -> Router:
    """Создаёт роутер раздела «start» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="start")
    router.message.register(cmd_start, CommandStart())
    return router
