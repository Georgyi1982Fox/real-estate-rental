"""Клавиатуры мастера поиска."""

from collections.abc import Sequence
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bina.application.dtos.pagination import Page
from bina.infrastructure.bot.formatters import district_name
from bina.infrastructure.bot.keyboards.callbacks import SearchCallback, SearchStep
from bina.infrastructure.bot.keyboards.filters import (
    PRICE_RANGES,
    ROOM_OPTIONS,
    price_label,
    rooms_button_label,
)
from bina.infrastructure.bot.keyboards.listings import favorite_buttons, pagination_row
from bina.infrastructure.bot.keyboards.menu import open_app_button
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import District, Listing

DISTRICTS_PER_PAGE = 12


def district_keyboard(
    districts: Sequence[District],
    page: int,
    language: str,
) -> InlineKeyboardMarkup:
    """Шаг 1: выбор района (по 2 в ряд, с пагинацией)."""
    pages = max(1, -(-len(districts) // DISTRICTS_PER_PAGE))
    page = min(max(page, 0), pages - 1)
    chunk = districts[page * DISTRICTS_PER_PAGE : (page + 1) * DISTRICTS_PER_PAGE]

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"🌍 {t(language, 'any_district')}",
        callback_data=SearchCallback(step=SearchStep.PRICE),
    )
    for district in chunk:
        builder.button(
            text=district_name(district, language),
            callback_data=SearchCallback(step=SearchStep.PRICE, district=district.id),
        )
    builder.adjust(1, 2)

    if pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(_district_page_button("◀️", page - 1))
        if page < pages - 1:
            nav.append(_district_page_button("▶️", page + 1))
        builder.row(*nav)
    return builder.as_markup()


def _district_page_button(text: str, page: int) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=SearchCallback(step=SearchStep.DISTRICT, page=page).pack(),
    )


def price_keyboard(district: UUID | None, language: str) -> InlineKeyboardMarkup:
    """Шаг 2: выбор бюджета."""
    builder = InlineKeyboardBuilder()
    for index in range(len(PRICE_RANGES)):
        builder.button(
            text=price_label(index, language),
            callback_data=SearchCallback(step=SearchStep.ROOMS, district=district, price=index),
        )
    builder.button(
        text=t(language, "any_price"),
        callback_data=SearchCallback(step=SearchStep.ROOMS, district=district),
    )
    builder.button(
        text=t(language, "back"),
        callback_data=SearchCallback(step=SearchStep.DISTRICT),
    )
    builder.adjust(2)
    return builder.as_markup()


def rooms_keyboard(
    district: UUID | None,
    price: int | None,
    language: str,
) -> InlineKeyboardMarkup:
    """Шаг 3: выбор количества комнат."""
    builder = InlineKeyboardBuilder()
    for index in range(len(ROOM_OPTIONS)):
        builder.button(
            text=rooms_button_label(index, language),
            callback_data=SearchCallback(
                step=SearchStep.RESULTS, district=district, price=price, rooms=index
            ),
        )
    builder.button(
        text=t(language, "any_rooms"),
        callback_data=SearchCallback(step=SearchStep.RESULTS, district=district, price=price),
    )
    builder.button(
        text=t(language, "back"),
        callback_data=SearchCallback(step=SearchStep.PRICE, district=district),
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
                callback_data=SearchCallback(step=SearchStep.DISTRICT).pack(),
            )
        ]
    )
    if mini_app_url:
        rows.append([open_app_button(language, mini_app_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
