"""Главное меню бота: все функции кнопками и «🏠 Главное меню» из любого ответа."""

import pytest
from aiogram.types import InlineKeyboardMarkup

from bina.infrastructure.bot.factory import COMMANDS
from bina.infrastructure.bot.keyboards.callbacks import MenuCallback, MenuSection
from bina.infrastructure.bot.keyboards.menu import home_menu

from .conftest import BotHarness


def texts(markup: InlineKeyboardMarkup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


async def test_start_shows_menu(harness: BotHarness) -> None:
    await harness.send("/start")
    assert "главное меню" in harness.last_text()
    buttons = texts(harness.last_markup())
    for label in (
        "🔍 Поиск",
        "❤️ Избранное",
        "⭐ Premium",
        "🎁 Пригласить друга",
        "🗓 Оплата аренды",
        "👤 Профиль",
        "❓ Помощь",
        "💬 Поддержка",
        "📄 Соглашение",
        "🔒 Конфиденциальность",
    ):
        assert label in buttons
    assert "📊 Админка" not in buttons, "админка — только владельцу"


@pytest.mark.parametrize(
    ("section", "expected"),
    [
        (MenuSection.SEARCH, "Шаг 1/3"),
        (MenuSection.FAVORITES, "избранном"),
        (MenuSection.PREMIUM, "Bina.ai Premium"),
        (MenuSection.INVITE, "Пригласите друзей"),
        (MenuSection.RENT, "Напоминания об оплате аренды"),
        (MenuSection.PROFILE, "Профиль"),
        (MenuSection.HELP, "/rent"),
        (MenuSection.SUPPORT, "Вопросы по оплате"),
        (MenuSection.TERMS, "Пользовательское соглашение"),
        (MenuSection.PRIVACY, "Политика конфиденциальности"),
    ],
)
async def test_menu_buttons_open_sections(
    harness: BotHarness, section: MenuSection, expected: str
) -> None:
    harness.store.add_district("Ваке")
    await harness.send("/start")
    await harness.press(MenuCallback(section=section).pack())
    assert expected in harness.last_text()


async def test_home_button_everywhere(harness: BotHarness) -> None:
    await harness.send("/start")
    for section in (MenuSection.HELP, MenuSection.PREMIUM, MenuSection.RENT):
        await harness.press(MenuCallback(section=section).pack())
        assert "🏠 Главное меню" in texts(harness.last_markup())
    await harness.press(MenuCallback(section=MenuSection.HOME).pack())
    assert "главное меню" in harness.last_text()
    # Кнопка внизу чата
    harness.reset()
    await harness.send("🏠 Главное меню")
    assert "главное меню" in harness.last_text()


# Команда → кнопка главного меню. Новая команда без кнопки — тест упадёт:
# владелец хочет видеть все функции кнопками, а не только в списке команд.
COMMAND_BUTTONS = {
    "search": MenuSection.SEARCH,
    "smart": MenuSection.SMART,
    "daily": MenuSection.DAILY,
    "favorites": MenuSection.FAVORITES,
    "profile": MenuSection.PROFILE,
    "premium": MenuSection.PREMIUM,
    "invite": MenuSection.INVITE,
    "rent": MenuSection.RENT,
    "terms": MenuSection.TERMS,
    "privacy": MenuSection.PRIVACY,
    "paysupport": MenuSection.SUPPORT,
    "help": MenuSection.HELP,
}


@pytest.mark.parametrize("language", ["ru", "en", "ka"])
def test_every_command_has_a_menu_button(language: str) -> None:
    assert set(COMMANDS[language]) == set(COMMAND_BUTTONS)
    sections = {
        MenuCallback.unpack(button.callback_data).section
        for row in home_menu(language, None).inline_keyboard
        for button in row
        if button.callback_data
    }
    assert set(COMMAND_BUTTONS.values()) <= sections
