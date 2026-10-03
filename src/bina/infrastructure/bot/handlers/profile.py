import json
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.subscriptions import effective_tier, is_premium
from bina.application.use_cases.account import AccountUseCase
from bina.application.use_cases.register_user import SUPPORTED_LANGUAGES
from bina.infrastructure.bot.formatters import format_number
from bina.infrastructure.bot.handlers.common import edit_or_answer
from bina.infrastructure.bot.keyboards.callbacks import (
    AccountAction,
    AccountCallback,
    LanguageCallback,
)
from bina.infrastructure.bot.keyboards.menu import main_menu, with_home
from bina.infrastructure.bot.keyboards.profile import delete_confirm_keyboard, language_keyboard
from bina.infrastructure.bot.texts import LANGUAGE_NAMES, all_variants, t
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.account import AccountRepository
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from bina.infrastructure.storage.photos import LocalPhotoStorage

DATE_FORMAT = "%d.%m.%Y"


async def cmd_profile(message: Message, session: AsyncSession, user: User) -> None:
    """/profile: данные пользователя и выбор языка."""
    favorites = await FavoritesRepository(session).count_by_user(user.id)
    await message.answer(
        render_profile(user, favorites, user.language),
        reply_markup=with_home(language_keyboard(user.language), user.language),
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
        with_home(language_keyboard(language), language),
        language,
    )
    if isinstance(callback.message, Message):
        # Reply-клавиатуру нельзя отредактировать, только прислать новую
        await callback.message.answer(
            t(language, "language_changed"),
            reply_markup=main_menu(language),
        )


async def on_account(
    callback: CallbackQuery,
    callback_data: AccountCallback,
    session: AsyncSession,
    user: User,
) -> None:
    """Свои данные (TASK-059, TASK-060): файл со всем, что хранится, или удаление."""
    language = user.language
    message = callback.message if isinstance(callback.message, Message) else None
    use_case = AccountUseCase(AccountRepository(session), LocalPhotoStorage())
    action = callback_data.action
    if action == AccountAction.EXPORT:
        await callback.answer()
        data = await use_case.export(user, datetime.now(UTC))
        document = BufferedInputFile(
            json.dumps(data, ensure_ascii=False, indent=2).encode(), "bina-my-data.json"
        )
        if message is not None:
            await message.answer_document(document, caption=t(language, "account_export_done"))
        return
    if action == AccountAction.ASK_DELETE:
        await callback.answer()
        paid = t(language, "account_delete_paid") if is_premium(user, datetime.now(UTC)) else ""
        if message is not None:
            await message.answer(
                t(language, "account_delete_ask", paid=paid),
                reply_markup=delete_confirm_keyboard(language),
            )
        return
    if action == AccountAction.CANCEL:
        await callback.answer(t(language, "account_delete_cancelled"))
        if message is not None:
            await message.delete_reply_markup()
        return
    await use_case.erase(user, datetime.now(UTC), session.commit)
    await callback.answer()
    if message is not None:
        await message.delete_reply_markup()
        # Меню больше не нужно: новый /start начнёт с чистого листа
        await message.answer(t(language, "account_deleted"), reply_markup=ReplyKeyboardRemove())


def render_profile(user: User, favorites: int, language: str) -> str:
    """Текст профиля."""
    now = datetime.now(UTC)
    expires = ""
    if is_premium(user, now) and user.subscription_expires_at is not None:
        expires = t(
            language,
            "subscription_until",
            date=user.subscription_expires_at.strftime(DATE_FORMAT),
        )
    return t(
        language,
        "profile",
        language=LANGUAGE_NAMES.get(user.language, user.language),
        tier=t(language, f"tier_{effective_tier(user, now).value}"),
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
    router.callback_query.register(on_account, AccountCallback.filter())
    return router
