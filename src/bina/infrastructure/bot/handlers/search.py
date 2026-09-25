from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackQueryFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bina.application.use_cases.search_listings import SearchListingsUseCase
from src.bina.infrastructure.bot.formatters import district_name, format_listings
from src.bina.infrastructure.bot.handlers.common import edit_or_answer
from src.bina.infrastructure.bot.keyboards.callbacks import SearchCallback, SearchStep
from src.bina.infrastructure.bot.keyboards.filters import (
    filters_from_callback,
    price_label,
    rooms_label,
)
from src.bina.infrastructure.bot.keyboards.search import (
    district_keyboard,
    price_keyboard,
    results_keyboard,
    rooms_keyboard,
)
from src.bina.infrastructure.bot.settings import BotSettings
from src.bina.infrastructure.bot.texts import all_variants, t
from src.bina.infrastructure.db.models import User
from src.bina.infrastructure.db.repositories.districts import DistrictsRepository
from src.bina.infrastructure.db.repositories.favorites import FavoritesRepository
from src.bina.infrastructure.db.repositories.listings import ListingsRepository


async def cmd_search(
    message: Message,
    session: AsyncSession,
    user: User,
    settings: BotSettings,
) -> None:
    """/search: шаг 1, выбор района.

    Если районов в БД нет, сразу показывает все объявления.
    """
    districts = await DistrictsRepository(session).list_all()
    if not districts:
        query = SearchCallback(step=SearchStep.RESULTS)
        text, markup = await _render_results(session, user, query, settings)
        await message.answer(t(user.language, "no_districts") + "\n\n" + text, reply_markup=markup)
        return
    await message.answer(
        t(user.language, "choose_district"),
        reply_markup=district_keyboard(districts, 0, user.language),
    )


async def on_district_step(
    callback: CallbackQuery,
    callback_data: SearchCallback,
    session: AsyncSession,
    user: User,
) -> None:
    """Шаг 1: (пере)показ списка районов на нужной странице."""
    districts = await DistrictsRepository(session).list_all()
    await edit_or_answer(
        callback,
        t(user.language, "choose_district"),
        district_keyboard(districts, callback_data.page, user.language),
        user.language,
    )


async def on_price_step(
    callback: CallbackQuery,
    callback_data: SearchCallback,
    session: AsyncSession,
    user: User,
) -> None:
    """Шаг 2: район выбран, выбор бюджета."""
    district = await _district_label(session, callback_data.district, user.language)
    await edit_or_answer(
        callback,
        t(user.language, "choose_price", district=district),
        price_keyboard(callback_data.district, user.language),
        user.language,
    )


async def on_rooms_step(
    callback: CallbackQuery,
    callback_data: SearchCallback,
    session: AsyncSession,
    user: User,
) -> None:
    """Шаг 3: бюджет выбран, выбор количества комнат."""
    district = await _district_label(session, callback_data.district, user.language)
    await edit_or_answer(
        callback,
        t(
            user.language,
            "choose_rooms",
            district=district,
            price=price_label(callback_data.price, user.language),
        ),
        rooms_keyboard(callback_data.district, callback_data.price, user.language),
        user.language,
    )


async def on_results(
    callback: CallbackQuery,
    callback_data: SearchCallback,
    session: AsyncSession,
    user: User,
    settings: BotSettings,
) -> None:
    """Результаты поиска (и переход между страницами)."""
    text, markup = await _render_results(session, user, callback_data, settings)
    await edit_or_answer(callback, text, markup, user.language)


async def _render_results(
    session: AsyncSession,
    user: User,
    query: SearchCallback,
    settings: BotSettings,
) -> tuple[str, InlineKeyboardMarkup]:
    """Текст и клавиатура страницы результатов."""
    language = user.language
    filters = filters_from_callback(query)
    use_case = SearchListingsUseCase(ListingsRepository(session))

    page = await use_case.execute(filters, page=max(query.page, 0), page_size=settings.page_size)
    if not page.items and page.total:
        # Страница «уехала» (объявления удалили): показываем последнюю
        page = await use_case.execute(filters, page=page.pages - 1, page_size=settings.page_size)

    summary = {
        "district": await _district_label(session, query.district, language),
        "price": price_label(query.price, language),
        "rooms": rooms_label(query.rooms, language),
    }
    if not page.items:
        text = t(language, "search_empty", **summary)
        return text, results_keyboard(page, query, set(), language, settings.mini_app_url)

    favorite_ids = await FavoritesRepository(session).filter_favorite_ids(
        user.id,
        [listing.id for listing in page.items],
    )
    parts = [
        t(language, "search_header", total=page.total, **summary),
        format_listings(page.items, page.page * page.page_size + 1, language),
    ]
    if page.pages > 1:
        parts.append(t(language, "page_counter", page=page.page + 1, pages=page.pages))
    parts.append(f"<i>{t(language, 'fav_hint')}</i>")
    markup = results_keyboard(page, query, favorite_ids, language, settings.mini_app_url)
    return "\n\n".join(parts), markup


async def _district_label(session: AsyncSession, district_id: UUID | None, language: str) -> str:
    """Название района для заголовков; «Любой район», если не выбран или не найден."""
    if district_id is not None:
        district = await DistrictsRepository(session).get_by_id(district_id)
        if district is not None:
            return district_name(district, language)
    return t(language, "any_district")


def _step_filter(step: SearchStep) -> CallbackQueryFilter:
    """Фильтр callback'ов мастера поиска по шагу."""
    return SearchCallback.filter(F.step == step)


def create_router() -> Router:
    """Создаёт роутер раздела «search» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="search")
    router.message.register(cmd_search, Command("search"))
    router.message.register(cmd_search, F.text.in_(all_variants("menu_search")))
    router.callback_query.register(on_district_step, _step_filter(SearchStep.DISTRICT))
    router.callback_query.register(on_price_step, _step_filter(SearchStep.PRICE))
    router.callback_query.register(on_rooms_step, _step_filter(SearchStep.ROOMS))
    router.callback_query.register(on_results, _step_filter(SearchStep.RESULTS))
    return router
