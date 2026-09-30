from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackQueryFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.cities import city_name
from bina.application.use_cases.search_listings import SearchListingsUseCase
from bina.infrastructure.bot.formatters import district_name, format_listings
from bina.infrastructure.bot.handlers.common import edit_or_answer
from bina.infrastructure.bot.keyboards.callbacks import SearchCallback, SearchStep
from bina.infrastructure.bot.keyboards.filters import (
    filters_from_callback,
    price_label,
    rooms_label,
)
from bina.infrastructure.bot.keyboards.search import (
    city_keyboard,
    district_keyboard,
    price_keyboard,
    results_keyboard,
    rooms_keyboard,
)
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import all_variants, t
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.districts import DistrictsRepository
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository


async def cmd_search(
    message: Message,
    session: AsyncSession,
    user: User,
    settings: BotSettings,
) -> None:
    """/search: выбор города (если их несколько, TASK-079), затем района.

    Если районов в БД нет, сразу показывает все объявления.
    """
    cities = await DistrictsRepository(session).cities()
    if not cities:
        query = SearchCallback(step=SearchStep.RESULTS)
        text, markup = await _render_results(session, user, query, settings)
        await message.answer(t(user.language, "no_districts") + "\n\n" + text, reply_markup=markup)
        return
    text, markup = await _first_step(session, user.language, cities)
    await message.answer(text, reply_markup=markup)


async def _first_step(
    session: AsyncSession, language: str, cities: list[str]
) -> tuple[str, InlineKeyboardMarkup]:
    """Город — если районы есть в нескольких городах, иначе сразу районы."""
    if len(cities) > 1:
        return t(language, "choose_city"), city_keyboard(cities, language)
    return await _district_step(session, language, cities[0] if cities else None, 0, cities)


async def _district_step(
    session: AsyncSession, language: str, city: str | None, page: int, cities: list[str]
) -> tuple[str, InlineKeyboardMarkup]:
    districts = await DistrictsRepository(session).list_all(city)
    markup = district_keyboard(districts, page, language, city, back_to_cities=len(cities) > 1)
    return t(language, "choose_district"), markup


async def on_city_step(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    """Выбор города (кнопки «Назад» и «Новый поиск»)."""
    cities = await DistrictsRepository(session).cities()
    text, markup = await _first_step(session, user.language, cities)
    await edit_or_answer(callback, text, markup, user.language)


async def on_district_step(
    callback: CallbackQuery,
    callback_data: SearchCallback,
    session: AsyncSession,
    user: User,
) -> None:
    """Шаг 1: (пере)показ списка районов города на нужной странице."""
    cities = await DistrictsRepository(session).cities()
    text, markup = await _district_step(
        session, user.language, callback_data.city, callback_data.page, cities
    )
    await edit_or_answer(callback, text, markup, user.language)


async def on_price_step(
    callback: CallbackQuery,
    callback_data: SearchCallback,
    session: AsyncSession,
    user: User,
) -> None:
    """Шаг 2: район выбран, выбор бюджета."""
    district = await _district_label(
        session, callback_data.district, user.language, callback_data.city
    )
    key = "choose_price_daily" if callback_data.daily else "choose_price"
    await edit_or_answer(
        callback,
        t(user.language, key, district=district),
        price_keyboard(
            callback_data.district, user.language, callback_data.city, callback_data.period
        ),
        user.language,
    )


async def on_rooms_step(
    callback: CallbackQuery,
    callback_data: SearchCallback,
    session: AsyncSession,
    user: User,
) -> None:
    """Шаг 3: бюджет выбран, выбор количества комнат."""
    district = await _district_label(
        session, callback_data.district, user.language, callback_data.city, callback_data.daily
    )
    await edit_or_answer(
        callback,
        t(
            user.language,
            "choose_rooms",
            district=district,
            price=price_label(callback_data.price, user.language, callback_data.daily),
        ),
        rooms_keyboard(
            callback_data.district,
            callback_data.price,
            user.language,
            callback_data.city,
            callback_data.period,
        ),
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
        "district": await _district_label(
            session, query.district, language, query.city, query.daily
        ),
        "price": price_label(query.price, language, query.daily),
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


async def _district_label(
    session: AsyncSession,
    district_id: UUID | None,
    language: str,
    city: str | None = None,
    daily: bool = False,
) -> str:
    """Название района для заголовков; «Батуми, любой район» или «Любой район».

    Для посуточной аренды (TASK-092) — с пометкой «🛏 посуточно».
    """
    label = await _place_label(session, district_id, language, city)
    return f"{label} · {t(language, 'period_daily_label')}" if daily else label


async def _place_label(
    session: AsyncSession, district_id: UUID | None, language: str, city: str | None
) -> str:
    if district_id is not None:
        district = await DistrictsRepository(session).get_by_id(district_id)
        if district is not None:
            return district_name(district, language)
    if city is not None:
        return t(language, "any_district_in", city=city_name(city, language))
    return t(language, "any_district")


def _step_filter(step: SearchStep) -> CallbackQueryFilter:
    """Фильтр callback'ов мастера поиска по шагу."""
    return SearchCallback.filter(F.step == step)


def create_router() -> Router:
    """Создаёт роутер раздела «search» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="search")
    router.message.register(cmd_search, Command("search"))
    router.message.register(cmd_search, F.text.in_(all_variants("menu_search")))
    router.callback_query.register(on_city_step, _step_filter(SearchStep.CITY))
    router.callback_query.register(on_district_step, _step_filter(SearchStep.DISTRICT))
    router.callback_query.register(on_price_step, _step_filter(SearchStep.PRICE))
    router.callback_query.register(on_rooms_step, _step_filter(SearchStep.ROOMS))
    router.callback_query.register(on_results, _step_filter(SearchStep.RESULTS))
    return router
