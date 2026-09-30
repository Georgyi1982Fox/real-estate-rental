"""Главное меню бота: все функции кнопками и возврат «🏠 Главное меню» из любого ответа."""

from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.embeddings import IEmbedder
from bina.application.subscriptions import Plan
from bina.infrastructure.bot.handlers import (
    admin,
    fallback,
    favorites,
    help,
    invite,
    legal,
    payments,
    profile,
    rent,
    search,
)
from bina.infrastructure.bot.keyboards.callbacks import MenuCallback, MenuSection
from bina.infrastructure.bot.keyboards.menu import home_menu
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import all_variants, t
from bina.infrastructure.db.models import User


async def send_home(message: Message, user: User, settings: BotSettings) -> None:
    """Сообщение «главное меню» со всеми функциями."""
    await message.answer(
        t(user.language, "menu_title"),
        reply_markup=home_menu(
            user.language, settings.mini_app_url, admin.is_admin(user, settings)
        ),
    )


async def on_home_text(
    message: Message, user: User, settings: BotSettings, state: FSMContext
) -> None:
    """Кнопка «🏠 Главное меню» внизу чата."""
    await state.clear()
    await send_home(message, user, settings)


async def on_menu(
    callback: CallbackQuery,
    callback_data: MenuCallback,
    user: User,
    session: AsyncSession,
    settings: BotSettings,
    plans: dict[str, Plan],
    bot: Bot,
    state: FSMContext,
    embedder: IEmbedder | None = None,
    **_: Any,
) -> None:
    """Нажатие кнопки главного меню: открывает раздел, как соответствующая команда."""
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer()
        return
    await callback.answer()
    section = callback_data.section
    if section == MenuSection.HOME:
        await state.clear()
        await send_home(message, user, settings)
    elif section == MenuSection.SEARCH:
        await search.cmd_search(message, session, user, settings)
    elif section == MenuSection.DAILY:
        await search.cmd_daily(message, session, user, settings)
    elif section == MenuSection.SMART:
        await fallback.cmd_smart(message, user, embedder)
    elif section == MenuSection.FAVORITES:
        await favorites.cmd_favorites(message, session, user, settings)
    elif section == MenuSection.PREMIUM:
        await payments.cmd_premium(message, user, plans, session)
    elif section == MenuSection.INVITE:
        await invite.cmd_invite(message, bot, user, session)
    elif section == MenuSection.RENT:
        await rent.cmd_rent(message, user, session, state)
    elif section == MenuSection.PROFILE:
        await profile.cmd_profile(message, session, user)
    elif section == MenuSection.HELP:
        await help.cmd_help(message, user)
    elif section == MenuSection.SUPPORT:
        await payments.cmd_paysupport(message, user)
    elif section == MenuSection.TERMS:
        await legal.cmd_terms(message, user)
    elif section == MenuSection.PRIVACY:
        await legal.cmd_privacy(message, user)
    elif section == MenuSection.ADMIN:
        await admin.cmd_admin(message, user, session, settings)


def create_router() -> Router:
    router = Router(name="menu")
    router.message.register(on_home_text, F.text.in_(all_variants("menu_home")))
    router.callback_query.register(on_menu, MenuCallback.filter())
    return router
