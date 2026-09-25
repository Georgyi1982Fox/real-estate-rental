"""Общие элементы списков объявлений: кнопки избранного и пагинация."""

from collections.abc import Sequence
from uuid import UUID

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bina.application.dtos.pagination import Page
from src.bina.infrastructure.bot.keyboards.callbacks import (
    FavoriteToggleCallback,
    NoopCallback,
)
from src.bina.infrastructure.db.models import Listing

FAV_ON = "★"
FAV_OFF = "☆"
FAV_BUTTONS_PER_ROW = 5


def favorite_buttons(
    listings: Sequence[Listing],
    start_index: int,
    favorite_ids: set[UUID],
) -> list[list[InlineKeyboardButton]]:
    """Ряды кнопок ☆/★ с номерами объявлений."""
    buttons = [
        InlineKeyboardButton(
            text=f"{FAV_ON if listing.id in favorite_ids else FAV_OFF} {start_index + offset}",
            callback_data=FavoriteToggleCallback(listing_id=listing.id).pack(),
        )
        for offset, listing in enumerate(listings)
    ]
    return [
        buttons[i : i + FAV_BUTTONS_PER_ROW]
        for i in range(0, len(buttons), FAV_BUTTONS_PER_ROW)
    ]


def pagination_row(
    page: Page[Listing],
    prev_callback: CallbackData | None,
    next_callback: CallbackData | None,
) -> list[InlineKeyboardButton]:
    """Ряд ◀️ n/N ▶️. Пустой, если страница одна."""
    if page.pages <= 1:
        return []
    row: list[InlineKeyboardButton] = []
    if page.has_prev and prev_callback is not None:
        row.append(InlineKeyboardButton(text="◀️", callback_data=prev_callback.pack()))
    row.append(
        InlineKeyboardButton(
            text=f"{page.page + 1}/{page.pages}",
            callback_data=NoopCallback().pack(),
        )
    )
    if page.has_next and next_callback is not None:
        row.append(InlineKeyboardButton(text="▶️", callback_data=next_callback.pack()))
    return row


def flip_favorite_button(
    markup: InlineKeyboardMarkup,
    callback_data: str,
    is_favorite: bool,
) -> InlineKeyboardMarkup:
    """Копия клавиатуры, в которой у кнопки ``callback_data`` переключена звезда.

    Позволяет обновить сообщение без повторного запроса страницы из БД.
    """
    rows = [
        [
            button.model_copy(
                update={"text": (FAV_ON if is_favorite else FAV_OFF) + button.text[1:]}
            )
            if button.callback_data == callback_data
            else button
            for button in row
        ]
        for row in markup.inline_keyboard
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
