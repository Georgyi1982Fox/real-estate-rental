"""``/invite``: ссылка для приглашения друзей и сколько уже приглашено (TASK-108)."""

from datetime import UTC, datetime

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.referrals import (
    FRIEND_DISCOUNT_PERCENT,
    MONTHLY_REWARDS,
    REWARD_DAYS,
    invite_link,
    month_start,
)
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.referrals import ReferralsRepository


async def cmd_invite(message: Message, bot: Bot, user: User, session: AsyncSession) -> None:
    referrals = ReferralsRepository(session)
    code = await referrals.code_for(user)
    me = await bot.me()
    invited, rewarded, _ = await referrals.stats(user.id, month_start(datetime.now(UTC)))
    await message.answer(
        t(
            user.language,
            "invite_info",
            percent=FRIEND_DISCOUNT_PERCENT,
            days=REWARD_DAYS,
            limit=MONTHLY_REWARDS,
            link=invite_link(me.username or "", code),
            invited=invited,
            rewarded=rewarded,
        ),
        reply_markup=with_home(None, user.language),
    )


def create_router() -> Router:
    router = Router(name="invite")
    router.message.register(cmd_invite, Command("invite"))
    return router
