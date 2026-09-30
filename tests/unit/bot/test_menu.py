"""Главное меню бота: все функции кнопками и «🏠 Главное меню» из любого ответа."""

import pytest
from aiogram.types import InlineKeyboardMarkup

from bina.infrastructure.bot.keyboards.callbacks import MenuCallback, MenuSection

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
