from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.use_cases.register_user import SUPPORTED_LANGUAGES
from bina.infrastructure.bot.formatters import format_number
from bina.infrastructure.bot.handlers.common import edit_or_answer
from bina.infrastructure.bot.keyboards.callbacks import LanguageCallback
from bina.infrastructure.bot.keyboards.menu import main_menu
from bina.infrastructure.bot.keyboards.profile import language_keyboard
from bina.infrastructure.bot.texts import LANGUAGE_NAMES, all_variants, t
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.users import UsersRepository

DATE_FORMAT = "%d.%m.%Y"


async def cmd_profile(message: Message, session: AsyncSession, user: User) -> None:
    """/profile: данные пользователя и выбор языка."""
    favorites = await FavoritesRepository(session).count_by_user(user.id)
    await message.answer(
        render_profile(user, favorites, user.language),
        reply_markup=language_keyboard(user.language),
    )


async def on_language(
    callback: CallbackQuery,
    callback_data: LanguageCallback,
    session: AsyncSession,
    user: User,
) -> None:
    """Смена языка: обновляет профиль и присылает меню на новом языке."""
    language = callback_data.code
    if language not in SUPPORTED_LANGUAGES:
        await callback.answer(t(user.language, "error"), show_alert=True)
        return
    if language == user.language:
        await callback.answer()
        return

    await UsersRepository(session).update_language(user.id, language)
    user.language = language

    favorites = await FavoritesRepository(session).count_by_user(user.id)
    await edit_or_answer(
        callback,
        render_profile(user, favorites, language),
        language_keyboard(language),
        language,
    )
    if isinstance(callback.message, Message):
        # Reply-клавиатуру нельзя отредактировать, только прислать новую
        await callback.message.answer(
            t(language, "language_changed"),
            reply_markup=main_menu(language),
        )


def render_profile(user: User, favorites: int, language: str) -> str:
    """Текст профиля."""
    expires = ""
    if user.subscription_expires_at is not None:
        expires = t(
            language,
            "subscription_until",
            date=user.subscription_expires_at.strftime(DATE_FORMAT),
        )
    return t(
        language,
        "profile",
        language=LANGUAGE_NAMES.get(user.language, user.language),
        tier=t(language, f"tier_{user.subscription_tier.value}"),
        expires=expires,
        balance=format_number(user.balance),
        favorites=favorites,
        since=user.created_at.strftime(DATE_FORMAT),
    )


def create_router() -> Router:
    """Создаёт роутер раздела «profile» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="profile")
    router.message.register(cmd_profile, Command("profile"))
    router.message.register(cmd_profile, F.text.in_(all_variants("menu_profile")))
    router.callback_query.register(on_language, LanguageCallback.filter())
    return router
