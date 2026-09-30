"""Главное меню и общие кнопки."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from bina.infrastructure.bot.keyboards.callbacks import MenuCallback, MenuSection
from bina.infrastructure.bot.texts import t


def main_menu(language: str) -> ReplyKeyboardMarkup:
    """Постоянная клавиатура внизу чата; «🏠 Главное меню» возвращает в начало."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t(language, "menu_search")),
                KeyboardButton(text=t(language, "menu_smart")),
            ],
            [
                KeyboardButton(text=t(language, "menu_favorites")),
                KeyboardButton(text=t(language, "menu_profile")),
            ],
            [KeyboardButton(text=t(language, "menu_home"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def _button(language: str, key: str, section: MenuSection) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=t(language, key), callback_data=MenuCallback(section=section).pack()
    )


def home_menu(language: str, mini_app_url: str | None, admin: bool = False) -> InlineKeyboardMarkup:
    """Все функции бота кнопками (сообщение «главное меню»), сгруппированные по смыслу.

    Сверху — Mini App, затем поиск жилья, «Сдать квартиру», подписка, личное,
    помощь и документы; внизу — админка (только владельцу).
    """
    rows: list[list[InlineKeyboardButton]] = []
    if mini_app_url:
        rows.append([open_app_button(language, mini_app_url)])
    rows += [
        # Поиск жилья: обычный и сразу посуточный (TASK-092), своими словами (TASK-012)
        [
            _button(language, "menu_search", MenuSection.SEARCH),
            _button(language, "menu_daily", MenuSection.DAILY),
        ],
        [
            _button(language, "menu_smart", MenuSection.SMART),
            _button(language, "menu_favorites", MenuSection.FAVORITES),
        ],
        # TASK-096: собственник сдаёт свою квартиру
        [_button(language, "menu_owner", MenuSection.OWNER)],
        [
            _button(language, "menu_premium", MenuSection.PREMIUM),
            _button(language, "menu_invite", MenuSection.INVITE),
        ],
        [
            _button(language, "menu_rent", MenuSection.RENT),
            _button(language, "menu_profile", MenuSection.PROFILE),
        ],
        [
            _button(language, "menu_help", MenuSection.HELP),
            _button(language, "menu_support", MenuSection.SUPPORT),
        ],
        [
            _button(language, "menu_terms", MenuSection.TERMS),
            _button(language, "menu_privacy", MenuSection.PRIVACY),
        ],
    ]
    if admin:
        admin_row = [_button(language, "menu_admin", MenuSection.ADMIN)]
        if mini_app_url:
            # Временная страница «Проверка функций» в Mini App (только владельцу)
            admin_row.append(
                InlineKeyboardButton(
                    text=t(language, "menu_lab"),
                    web_app=WebAppInfo(url=mini_app_url.rstrip("/") + "/lab"),
                )
            )
        rows.append(admin_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def home_button(language: str) -> InlineKeyboardButton:
    """Кнопка «🏠 Главное меню» под ответом."""
    return _button(language, "menu_home", MenuSection.HOME)


def with_home(markup: InlineKeyboardMarkup | None, language: str) -> InlineKeyboardMarkup:
    """Та же клавиатура плюс «🏠 Главное меню» последней строкой."""
    rows = list(markup.inline_keyboard) if markup else []
    return InlineKeyboardMarkup(inline_keyboard=[*rows, [home_button(language)]])


def open_app_button(language: str, mini_app_url: str) -> InlineKeyboardButton:
    """Кнопка открытия Telegram Mini App."""
    return InlineKeyboardButton(
        text=t(language, "open_app"),
        web_app=WebAppInfo(url=mini_app_url),
    )
