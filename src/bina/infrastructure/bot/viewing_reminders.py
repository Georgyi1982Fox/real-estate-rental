"""Напоминание о просмотре за 2 часа обоим — арендатору и хозяину (TASK-112).

Работает внутри процесса бота: раз в минуту ищет подтверждённые просмотры, до
которых осталось не больше двух часов, и о которых ещё не напоминали.
"""

import asyncio
import contextlib
from datetime import UTC, datetime

import structlog
from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.use_cases.chat import ChatUseCase
from bina.infrastructure.bot.handlers.chat import deliver, render_reminder
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.db.repositories.chat import ChatRepository
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository

logger = structlog.get_logger(__name__)

CHECK_EVERY_SECONDS = 60


async def send_viewing_reminders(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession], now: datetime
) -> int:
    """Отправляет напоминания; возвращает число просмотров, о которых напомнили."""
    async with session_factory() as session:
        use_case = ChatUseCase(ChatRepository(session))
        notices = await use_case.due_reminders(now)
        for notice in notices:
            for person in (notice.tenant, notice.owner):
                await deliver(
                    bot,
                    person.telegram_id,
                    render_reminder(notice, person),
                    with_home(None, person.language),
                )
            await use_case.mark_reminded(notice.viewing, now)
        await session.commit()
    return len(notices)


async def reminders_loop(bot: Bot, session_factory: async_sessionmaker[AsyncSession]) -> None:
    while True:
        try:
            sent = await send_viewing_reminders(bot, session_factory, datetime.now(UTC))
            if sent:
                logger.info("Viewing reminders sent", viewings=sent)
        except Exception as exc:  # noqa: BLE001 - сеть/БД: попробуем через минуту
            logger.warning("Viewing reminders failed", error=str(exc))
        await asyncio.sleep(CHECK_EVERY_SECONDS)


async def link_owner_listings(bot: Bot, session_factory: async_sessionmaker[AsyncSession]) -> None:
    """«Написать» у объявлений хозяев, размещённых раньше, — тоже в чат через бота (TASK-111)."""
    try:
        me = await bot.me()
        if not me.username:
            return
        async with session_factory() as session:
            linked = await OwnerListingsRepository(session).link_to_chat(me.username)
            await session.commit()
    except Exception as exc:  # noqa: BLE001 - не мешаем запуску бота
        logger.warning("Owner listings not linked to chat", error=str(exc))
        return
    if linked:
        logger.info("Owner listings linked to chat", listings=linked)


def register(dispatcher: Dispatcher, session_factory: async_sessionmaker[AsyncSession]) -> None:
    """При старте: ссылки «Написать» и цикл напоминаний; остановка при выключении."""
    tasks: list[asyncio.Task[None]] = []

    async def on_startup(bot: Bot) -> None:
        await link_owner_listings(bot, session_factory)
        tasks.append(asyncio.create_task(reminders_loop(bot, session_factory)))

    async def on_shutdown() -> None:
        for task in tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        tasks.clear()

    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)
