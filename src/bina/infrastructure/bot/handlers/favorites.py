from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.errors import ListingNotFoundError
from bina.application.use_cases.favorites import GetFavoritesUseCase, ToggleFavoriteUseCase
from bina.infrastructure.bot.formatters import format_listings
from bina.infrastructure.bot.handlers.common import edit_or_answer
from bina.infrastructure.bot.keyboards.callbacks import (
    FavoritesPageCallback,
    FavoriteToggleCallback,
    NoopCallback,
)
from bina.infrastructure.bot.keyboards.favorites import favorites_keyboard
from bina.infrastructure.bot.keyboards.listings import flip_favorite_button
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import all_variants, t
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository


async def cmd_favorites(
    message: Message,
    session: AsyncSession,
    user: User,
    settings: BotSettings,
) -> None:
    """/favorites: первая страница избранного."""
    text, markup = await _render_favorites(session, user, 0, settings)
    await message.answer(text, reply_markup=markup)


async def on_favorites_page(
    callback: CallbackQuery,
    callback_data: FavoritesPageCallback,
    session: AsyncSession,
    user: User,
    settings: BotSettings,
) -> None:
    """Переход между страницами избранного."""
    text, markup = await _render_favorites(session, user, callback_data.page, settings)
    await edit_or_answer(callback, text, markup, user.language)


async def on_favorite_toggle(
    callback: CallbackQuery,
    callback_data: FavoriteToggleCallback,
    session: AsyncSession,
    user: User,
) -> None:
    """☆/★ под списком: переключает избранное и обновляет только звезду на кнопке.

    Работает одинаково в результатах поиска и в избранном: в избранном снятая
    звезда оставляет объявление на экране, чтобы действие можно было отменить.
    """
    use_case = ToggleFavoriteUseCase(FavoritesRepository(session), ListingsRepository(session))
    try:
        is_favorite = await use_case.execute(user.id, callback_data.listing_id)
    except ListingNotFoundError:
        await callback.answer(t(user.language, "listing_unavailable"), show_alert=True)
        return

    message = callback.message
    if isinstance(message, Message) and message.reply_markup is not None and callback.data:
        await message.edit_reply_markup(
            reply_markup=flip_favorite_button(message.reply_markup, callback.data, is_favorite)
        )
    await callback.answer(t(user.language, "fav_added" if is_favorite else "fav_removed"))


async def on_noop(callback: CallbackQuery) -> None:
    """Неактивная кнопка счётчика страниц."""
    await callback.answer()


async def _render_favorites(
    session: AsyncSession,
    user: User,
    page_number: int,
    settings: BotSettings,
) -> tuple[str, InlineKeyboardMarkup | None]:
    """Текст и клавиатура страницы избранного."""
    language = user.language
    use_case = GetFavoritesUseCase(FavoritesRepository(session))
    page = await use_case.execute(user.id, page=max(page_number, 0), page_size=settings.page_size)
    if not page.items and page.total:
        page = await use_case.execute(user.id, page=page.pages - 1, page_size=settings.page_size)

    if not page.items:
        return t(language, "favorites_empty"), None

    parts = [
        t(language, "favorites_header", total=page.total),
        format_listings(page.items, page.page * page.page_size + 1, language),
    ]
    if page.pages > 1:
        parts.append(t(language, "page_counter", page=page.page + 1, pages=page.pages))
    parts.append(f"<i>{t(language, 'fav_hint')}</i>")
    return "\n\n".join(parts), favorites_keyboard(page, language, settings.mini_app_url)


def create_router() -> Router:
    """Создаёт роутер раздела «favorites» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="favorites")
    router.message.register(cmd_favorites, Command("favorites"))
    router.message.register(cmd_favorites, F.text.in_(all_variants("menu_favorites")))
    router.callback_query.register(on_favorites_page, FavoritesPageCallback.filter())
    router.callback_query.register(on_favorite_toggle, FavoriteToggleCallback.filter())
    router.callback_query.register(on_noop, NoopCallback.filter())
    return router
