"""Клавиатура списка избранного."""

from aiogram.types import InlineKeyboardMarkup

from src.bina.application.dtos.pagination import Page
from src.bina.infrastructure.bot.keyboards.callbacks import FavoritesPageCallback
from src.bina.infrastructure.bot.keyboards.listings import favorite_buttons, pagination_row
from src.bina.infrastructure.bot.keyboards.menu import open_app_button
from src.bina.infrastructure.db.models import Listing


def favorites_keyboard(
    page: Page[Listing],
    language: str,
    mini_app_url: str | None = None,
) -> InlineKeyboardMarkup:
    """Кнопки ★ (все объявления на странице в избранном) и пагинация."""
    favorite_ids = {listing.id for listing in page.items}
    rows = favorite_buttons(page.items, page.page * page.page_size + 1, favorite_ids)
    nav = pagination_row(
        page,
        FavoritesPageCallback(page=page.page - 1),
        FavoritesPageCallback(page=page.page + 1),
    )
    if nav:
        rows.append(nav)
    if mini_app_url:
        rows.append([open_app_button(language, mini_app_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
