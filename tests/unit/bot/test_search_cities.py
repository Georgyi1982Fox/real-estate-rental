"""Поиск в боте по городам (TASK-079)."""

from aiogram.types import InlineKeyboardMarkup

from bina.infrastructure.bot.keyboards.callbacks import SearchCallback, SearchStep

from .conftest import BotHarness


def buttons(markup: InlineKeyboardMarkup) -> dict[str, str]:
    return {
        button.text: button.callback_data or "" for row in markup.inline_keyboard for button in row
    }


async def test_one_city_skips_city_step(harness: BotHarness) -> None:
    harness.store.add_district("Ваке")
    await harness.send("/search")
    assert "Шаг 1/3" in harness.last_text()


async def test_choose_batumi_then_district(harness: BotHarness) -> None:
    vake = harness.store.add_district("Ваке")
    old = harness.store.add_district("Старый Батуми", "Old Batumi", city="batumi")
    harness.store.add_listing(vake, price=1000)
    harness.store.add_listing(old, price=900)

    await harness.send("/search")
    assert "Выберите город" in harness.last_text()
    city_buttons = buttons(harness.last_markup())
    assert set(city_buttons) == {"🏙 Тбилиси", "🏙 Батуми"}

    await harness.press(city_buttons["🏙 Батуми"])
    district_buttons = buttons(harness.last_markup())
    assert "Старый Батуми" in district_buttons
    assert "Ваке" not in district_buttons
    assert "⬅️ Назад" in district_buttons, "назад к выбору города"

    # «Любой район» в Батуми → любые цена и комнаты: только объявление Батуми
    await harness.press(SearchCallback(step=SearchStep.RESULTS, city="batumi").pack())
    text = harness.last_text()
    assert "Найдено: <b>1</b>" in text
    assert "Батуми, любой район" in text


def test_callback_fits_telegram_limit() -> None:
    from uuid import uuid4

    data = SearchCallback(
        step=SearchStep.RESULTS, district=uuid4(), price=4, rooms=3, page=99, city="batumi"
    ).pack()
    assert len(data.encode()) <= 64


async def test_daily_rent_from_menu_button(harness: BotHarness) -> None:
    """TASK-092: «🛏 Посуточно» — весь поиск сразу по посуточной аренде."""
    vake = harness.store.add_district("Ваке")
    old = harness.store.add_district("Старый Батуми", "Old Batumi", city="batumi")
    harness.store.add_listing(vake, price=1500, title_ru="Помесячно")
    harness.store.add_listing(old, price=70, title_ru="Посуточно у моря", rent_period="daily")

    await harness.send("🛏 Посуточно")
    assert "Посуточная аренда" in harness.last_text()

    await harness.press(buttons(harness.last_markup())["🏙 Батуми"])
    assert "Посуточная аренда" in harness.last_text()
    await harness.press(buttons(harness.last_markup())["🌍 Любой район"])
    assert "Бюджет за сутки" in harness.last_text()
    price_buttons = buttons(harness.last_markup())
    assert "до 80 ₾" in price_buttons and "📅 Помесячно" in price_buttons

    await harness.press(price_buttons["до 80 ₾"])
    await harness.press(buttons(harness.last_markup())["Любое"])
    text = harness.last_text()
    assert "Найдено: <b>1</b>" in text
    assert "Посуточно у моря" in text and "70 ₾ / сутки" in text
    assert "🛏 посуточно" in text


async def test_daily_command(harness: BotHarness) -> None:
    harness.store.add_district("Ваке")
    await harness.send("/daily")
    assert "Посуточная аренда" in harness.last_text()
    assert "Шаг 1/3" in harness.last_text()
