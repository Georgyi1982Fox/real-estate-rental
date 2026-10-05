"""Клавиатура списка избранного."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bina.application.dtos.pagination import Page
from bina.infrastructure.bot.keyboards.callbacks import (
    FavoritesPageCallback,
    HistoryCallback,
    RecommendCallback,
)
from bina.infrastructure.bot.keyboards.listings import (
    chat_buttons,
    favorite_buttons,
    pagination_row,
)
from bina.infrastructure.bot.keyboards.menu import open_app_button
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import Listing


def favorites_keyboard(
    page: Page[Listing],
    language: str,
    mini_app_url: str | None = None,
) -> InlineKeyboardMarkup:
    """Кнопки ★ (все объявления на странице в избранном) и пагинация."""
    favorite_ids = {listing.id for listing in page.items}
    start = page.page * page.page_size + 1
    rows = favorite_buttons(page.items, start, favorite_ids) + chat_buttons(page.items, start)
    nav = pagination_row(
        page,
        FavoritesPageCallback(page=page.page - 1),
        FavoritesPageCallback(page=page.page + 1),
    )
    if nav:
        rows.append(nav)
    # TASK-076: похожие на избранное
    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, "rec_button"), callback_data=RecommendCallback().pack()
            )
        ]
    )
    # TASK-075: недавно смотрели
    rows.append(
        [
            InlineKeyboardButton(
                text=t(language, "history_button"), callback_data=HistoryCallback().pack()
            )
        ]
    )
    if mini_app_url:
        rows.append([open_app_button(language, mini_app_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
