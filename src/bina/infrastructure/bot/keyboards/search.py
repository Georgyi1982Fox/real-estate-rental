"""Клавиатуры мастера поиска."""

from collections.abc import Sequence
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bina.application.cities import city_name
from bina.application.dtos.pagination import Page
from bina.infrastructure.bot.formatters import district_name
from bina.infrastructure.bot.keyboards.callbacks import DAILY_PERIOD, SearchCallback, SearchStep
from bina.infrastructure.bot.keyboards.filters import (
    ROOM_OPTIONS,
    price_label,
    price_ranges,
    rooms_button_label,
)
from bina.infrastructure.bot.keyboards.listings import favorite_buttons, pagination_row
from bina.infrastructure.bot.keyboards.menu import open_app_button
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import District, Listing

DISTRICTS_PER_PAGE = 12


def city_keyboard(cities: Sequence[str], language: str) -> InlineKeyboardMarkup:
    """Выбор города (TASK-079), если районы есть больше чем в одном городе."""
    builder = InlineKeyboardBuilder()
    for code in cities:
        builder.button(
            text=f"🏙 {city_name(code, language)}",
            callback_data=SearchCallback(step=SearchStep.DISTRICT, city=code),
        )
    builder.adjust(2)
    return builder.as_markup()


def district_keyboard(
    districts: Sequence[District],
    page: int,
    language: str,
    city: str | None = None,
    *,
    back_to_cities: bool = False,
) -> InlineKeyboardMarkup:
    """Шаг 1: выбор района города (по 2 в ряд, с пагинацией)."""
    pages = max(1, -(-len(districts) // DISTRICTS_PER_PAGE))
    page = min(max(page, 0), pages - 1)
    chunk = districts[page * DISTRICTS_PER_PAGE : (page + 1) * DISTRICTS_PER_PAGE]

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"🌍 {t(language, 'any_district')}",
        callback_data=SearchCallback(step=SearchStep.PRICE, city=city),
    )
    for district in chunk:
        builder.button(
            text=district_name(district, language),
            callback_data=SearchCallback(step=SearchStep.PRICE, district=district.id, city=city),
        )
    builder.adjust(1, 2)

    if pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(_district_page_button("◀️", page - 1, city))
        if page < pages - 1:
            nav.append(_district_page_button("▶️", page + 1, city))
        builder.row(*nav)
    if back_to_cities:
        builder.row(
            InlineKeyboardButton(
                text=t(language, "back"),
                callback_data=SearchCallback(step=SearchStep.CITY).pack(),
            )
        )
    return builder.as_markup()


def _district_page_button(text: str, page: int, city: str | None) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=SearchCallback(step=SearchStep.DISTRICT, page=page, city=city).pack(),
    )


def price_keyboard(
    district: UUID | None, language: str, city: str | None = None, period: str | None = None
) -> InlineKeyboardMarkup:
    """Шаг 2: выбор бюджета; кнопка переключает помесячную и посуточную аренду (TASK-092)."""
    daily = period == DAILY_PERIOD
    builder = InlineKeyboardBuilder()
    for index in range(len(price_ranges(daily))):
        builder.button(
            text=price_label(index, language, daily),
            callback_data=SearchCallback(
                step=SearchStep.ROOMS, district=district, price=index, city=city, period=period
            ),
        )
    builder.button(
        text=t(language, "any_price"),
        callback_data=SearchCallback(
            step=SearchStep.ROOMS, district=district, city=city, period=period
        ),
    )
    builder.button(
        text=t(language, "period_to_monthly" if daily else "period_to_daily"),
        callback_data=SearchCallback(
            step=SearchStep.PRICE,
            district=district,
            city=city,
            period=None if daily else DAILY_PERIOD,
        ),
    )
    builder.button(
        text=t(language, "back"),
        callback_data=SearchCallback(step=SearchStep.DISTRICT, city=city),
    )
    builder.adjust(2)
    return builder.as_markup()


def rooms_keyboard(
    district: UUID | None,
    price: int | None,
    language: str,
    city: str | None = None,
    period: str | None = None,
) -> InlineKeyboardMarkup:
    """Шаг 3: выбор количества комнат."""
    builder = InlineKeyboardBuilder()
    for index in range(len(ROOM_OPTIONS)):
        builder.button(
            text=rooms_button_label(index, language),
            callback_data=SearchCallback(
                step=SearchStep.RESULTS,
                district=district,
                price=price,
                rooms=index,
                city=city,
                period=period,
            ),
        )
    builder.button(
        text=t(language, "any_rooms"),
        callback_data=SearchCallback(
            step=SearchStep.RESULTS, district=district, price=price, city=city, period=period
        ),
    )
    builder.button(
        text=t(language, "back"),
        callback_data=SearchCallback(
            step=SearchStep.PRICE, district=district, city=city, period=period
        ),
    )
    builder.adjust(len(ROOM_OPTIONS), 1, 1)
    return builder.as_markup()


def results_keyboard(
    page: Page[Listing],
    query: SearchCallback,
    favorite_ids: set[UUID],
    language: str,
    mini_app_url: str | None = None,
) -> InlineKeyboardMarkup:
    """Результаты: кнопки избранного, пагинация, новый поиск, Mini App."""
    rows = favorite_buttons(page.items, page.page * page.page_size + 1, favorite_ids)

    def to_page(number: int) -> SearchCallback:
        return query.model_copy(update={"step": SearchStep.RESULTS, "page": number})

    nav = pagination_row(page, to_page(page.page - 1), to_page(page.page + 1))
    if nav:
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, "new_search"),
                callback_data=SearchCallback(step=SearchStep.CITY).pack(),
            )
        ]
    )
    if mini_app_url:
        rows.append([open_app_button(language, mini_app_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
