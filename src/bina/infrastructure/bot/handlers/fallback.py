"""Любой текст, который не команда и не кнопка: умный поиск по смыслу (TASK-012).

«Двушка с балконом в Ваке до 1500» → объявления, близкие по смыслу. Если умный
поиск недоступен (нет ключа AI или сервис не ответил) — подсказка про меню.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.ports.embeddings import EmbeddingsError, IEmbedder
from bina.application.rent_period import period_from_text
from bina.application.semantic_search import is_smart_query
from bina.application.use_cases.smart_search import SmartSearchUseCase
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.bot.formatters import format_listings
from bina.infrastructure.bot.keyboards.listings import favorite_buttons
from bina.infrastructure.bot.keyboards.menu import open_app_button, with_home
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import all_variants, t
from bina.infrastructure.db.models import Listing, User
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository

# Длиннее запрос не нужен (и не тратим токены на простыни текста)
MAX_QUERY = 200


async def on_unknown_message(
    message: Message,
    user: User,
    session: AsyncSession,
    settings: BotSettings,
    embedder: IEmbedder | None = None,
) -> None:
    """Текст — умный поиск; иначе подсказка про меню и /help."""
    query = clean_text(message.text or "")[:MAX_QUERY]
    if embedder is not None and is_smart_query(query) and not query.startswith("/"):
        try:
            page = await SmartSearchUseCase(ListingsRepository(session), embedder).execute(
                ListingSearchFilters(query=query, rent_period=period_from_text(query)),
                page=0,
                page_size=settings.page_size,
            )
        except EmbeddingsError:
            page = None
        if page is not None:
            await _answer_results(message, user, session, settings, query, page.items)
            return
    await message.answer(t(user.language, "unknown"))


async def _answer_results(
    message: Message,
    user: User,
    session: AsyncSession,
    settings: BotSettings,
    query: str,
    items: list[Listing],
) -> None:
    language = user.language
    if not items:
        await message.answer(
            t(language, "smart_empty", query=query), reply_markup=with_home(None, language)
        )
        return
    favorite_ids = await FavoritesRepository(session).filter_favorite_ids(
        user.id, [listing.id for listing in items]
    )
    rows = favorite_buttons(items, 1, favorite_ids)
    if settings.mini_app_url:
        rows.append([open_app_button(language, settings.mini_app_url)])
    text = "\n\n".join(
        [
            t(language, "smart_header", query=query),
            format_listings(items, 1, language),
            f"<i>{t(language, 'smart_hint')}</i>",
        ]
    )
    await message.answer(
        text, reply_markup=with_home(InlineKeyboardMarkup(inline_keyboard=rows), language)
    )


async def cmd_smart(message: Message, user: User, embedder: IEmbedder | None = None) -> None:
    """/smart и кнопка «🧠 Умный поиск»: как пользоваться (следующее сообщение — запрос)."""
    key = "smart_intro" if embedder is not None else "smart_unavailable"
    await message.answer(t(user.language, key), reply_markup=with_home(None, user.language))


def create_router() -> Router:
    """Создаёт роутер раздела «fallback» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="fallback")
    router.message.register(cmd_smart, Command("smart"))
    router.message.register(cmd_smart, F.text.in_(all_variants("menu_smart")))
    router.message.register(on_unknown_message)
    return router
