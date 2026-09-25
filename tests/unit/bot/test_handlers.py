"""Сценарии бота целиком: апдейт -> middleware -> роутеры -> вызовы Telegram API."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageReplyMarkup,
    EditMessageText,
    SendMessage,
)
from aiogram.types import (
    Chat,
    InaccessibleMessage,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

from bina.application.use_cases.search_listings import SearchListingsUseCase
from bina.infrastructure.bot.keyboards.callbacks import (
    FavoritesPageCallback,
    FavoriteToggleCallback,
    LanguageCallback,
    SearchCallback,
    SearchStep,
)

from .conftest import BotHarness


def buttons(markup: InlineKeyboardMarkup) -> list[list[str]]:
    """Подписи кнопок клавиатуры."""
    return [[button.text for button in row] for row in markup.inline_keyboard]


# --------------------------------------------------------------------------- /start, /help


async def test_start_registers_new_user(harness: BotHarness) -> None:
    await harness.send("/start")

    assert harness.user.telegram_id == 777
    assert harness.user.language == "ru"
    [message] = harness.telegram.of(SendMessage)
    assert "Добро пожаловать" in message.text
    assert isinstance(message.reply_markup, ReplyKeyboardMarkup)
    assert harness.sessions[-1].commit.await_count == 1


async def test_start_greets_returning_user(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.reset()

    await harness.send("/start")

    assert "С возвращением" in harness.last_text()
    assert len(harness.store.users) == 1


async def test_language_taken_from_telegram_on_registration(harness: BotHarness) -> None:
    await harness.send("/help", language_code="en-US")

    assert harness.user.language == "en"
    assert "rentals in Georgia" in harness.last_text()


async def test_georgian_user_gets_english_interface(harness: BotHarness) -> None:
    await harness.send("/help", language_code="ka")

    assert harness.user.language == "ka"
    assert "rentals in Georgia" in harness.last_text()


async def test_unknown_message(harness: BotHarness) -> None:
    await harness.send("привет")

    assert "Не понял" in harness.last_text()


# --------------------------------------------------------------------------- search


async def test_search_starts_with_district_picker(harness: BotHarness) -> None:
    harness.store.add_district("Сабуртало")
    harness.store.add_district("Ваке")

    await harness.send("🔍 Поиск")

    assert "Шаг 1/3" in harness.last_text()
    assert buttons(harness.last_markup()) == [["🌍 Любой район"], ["Ваке", "Сабуртало"]]


async def test_search_command_works_like_menu_button(harness: BotHarness) -> None:
    harness.store.add_district("Ваке")

    await harness.send("/search")

    assert "Шаг 1/3" in harness.last_text()


async def test_search_without_districts_shows_all_listings(harness: BotHarness) -> None:
    district = harness.store.add_district("Ваке")
    harness.store.districts.clear()
    harness.store.add_listing(district, title_ru="Единственная")

    await harness.send("/search")

    text = harness.last_text()
    assert "Районы ещё не загружены" in text
    assert "Единственная" in text


async def test_wizard_steps_show_selected_filters(harness: BotHarness) -> None:
    vake = harness.store.add_district("Ваке")
    await harness.send("/start")

    await harness.press(SearchCallback(step=SearchStep.PRICE, district=vake.id).pack())
    assert "📍 Ваке" in harness.last_text()
    assert "Шаг 2/3" in harness.last_text()

    await harness.press(SearchCallback(step=SearchStep.ROOMS, district=vake.id, price=1).pack())
    assert "📍 Ваке · 💰 1 000–1 500 ₾" in harness.last_text()  # noqa: RUF001
    assert buttons(harness.last_markup())[0] == ["1", "2", "3", "4+"]


async def test_results_apply_filters_and_paginate(harness: BotHarness) -> None:
    vake = harness.store.add_district("Ваке")
    other = harness.store.add_district("Сабуртало")
    for price in (900, 1000, 1200, 1400, 1500):
        harness.store.add_listing(vake, price=price, title_ru=f"Ваке {price}")
    harness.store.add_listing(vake, price=1200, rooms=4, title_ru="Большая")
    harness.store.add_listing(other, price=1200, title_ru="Чужой район")

    query = SearchCallback(step=SearchStep.RESULTS, district=vake.id, price=1, rooms=1)
    await harness.press(query.pack())

    text = harness.last_text()
    assert "Найдено: <b>4</b>" in text
    assert "Страница 1 из 2" in text
    assert "Ваке 900" not in text and "Большая" not in text and "Чужой район" not in text
    # новые сверху: 1500, 1400, 1200 на первой странице
    assert text.index("Ваке 1500") < text.index("Ваке 1400") < text.index("Ваке 1200")
    assert buttons(harness.last_markup()) == [
        ["☆ 1", "☆ 2", "☆ 3"],
        ["1/2", "▶️"],
        ["🔄 Новый поиск"],
    ]

    await harness.press(query.model_copy(update={"page": 1}).pack())
    assert "Ваке 1000" in harness.last_text()
    assert buttons(harness.last_markup())[:2] == [["☆ 4"], ["◀️", "2/2"]]


async def test_results_page_out_of_range_shows_last_page(harness: BotHarness) -> None:
    vake = harness.store.add_district("Ваке")
    for _ in range(4):
        harness.store.add_listing(vake)

    await harness.press(SearchCallback(step=SearchStep.RESULTS, page=10).pack())

    assert "Страница 2 из 2" in harness.last_text()


async def test_results_empty(harness: BotHarness) -> None:
    harness.store.add_district("Ваке")

    await harness.press(SearchCallback(step=SearchStep.RESULTS, price=4).pack())

    assert "ничего не найдено" in harness.last_text()
    assert "от 4 000 ₾" in harness.last_text()


async def test_results_mark_existing_favorites(harness: BotHarness) -> None:
    vake = harness.store.add_district("Ваке")
    first = harness.store.add_listing(vake)
    harness.store.add_listing(vake)
    await harness.send("/start")
    harness.store.favorites.append((harness.user.id, first.id))

    await harness.press(SearchCallback(step=SearchStep.RESULTS).pack())

    assert buttons(harness.last_markup())[0] == ["☆ 1", "★ 2"]


async def test_results_show_mini_app_button_when_configured(
    harness: BotHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness.store.add_listing(harness.store.add_district("Ваке"))
    settings = harness.dispatcher["settings"]
    harness.dispatcher["settings"] = type(settings)(token=settings.token, mini_app_url="https://app")

    await harness.press(SearchCallback(step=SearchStep.RESULTS).pack())

    last_row = harness.last_markup().inline_keyboard[-1]
    assert last_row[0].web_app.url == "https://app"


# --------------------------------------------------------------------------- favorites


async def test_toggle_favorite_flips_star_in_place(harness: BotHarness) -> None:
    vake = harness.store.add_district("Ваке")
    harness.store.add_listing(vake)
    harness.store.add_listing(vake)
    await harness.press(SearchCallback(step=SearchStep.RESULTS).pack())
    markup = harness.last_markup()
    second = markup.inline_keyboard[0][1].callback_data
    harness.reset()

    await harness.press(second, markup)

    [edit] = harness.telegram.of(EditMessageReplyMarkup)
    assert buttons(edit.reply_markup)[0] == ["☆ 1", "★ 2"]
    [answer] = harness.telegram.of(AnswerCallbackQuery)
    assert answer.text == "★ Добавлено в избранное"
    assert len(harness.store.favorites) == 1

    harness.reset()
    await harness.press(second, edit.reply_markup)

    [edit] = harness.telegram.of(EditMessageReplyMarkup)
    assert buttons(edit.reply_markup)[0] == ["☆ 1", "☆ 2"]
    assert harness.store.favorites == []


async def test_toggle_unavailable_listing_shows_alert(harness: BotHarness) -> None:
    await harness.press(FavoriteToggleCallback(listing_id=uuid4()).pack())

    [answer] = harness.telegram.of(AnswerCallbackQuery)
    assert answer.show_alert is True
    assert "больше недоступно" in (answer.text or "")
    assert harness.telegram.of(EditMessageReplyMarkup) == []


async def test_favorites_empty(harness: BotHarness) -> None:
    await harness.send("❤️ Избранное")

    assert "пока пусто" in harness.last_text()
    assert harness.last_markup() is None


async def test_favorites_list_and_pagination(harness: BotHarness) -> None:
    vake = harness.store.add_district("Ваке")
    await harness.send("/start")
    for index in range(4):
        listing = harness.store.add_listing(vake, title_ru=f"Избранное {index}")
        harness.store.favorites.append((harness.user.id, listing.id))

    await harness.send("/favorites")

    text = harness.last_text()
    assert "Избранное</b>: 4" in text
    assert "Избранное 3" in text and "Избранное 0" not in text
    assert buttons(harness.last_markup()) == [["★ 1", "★ 2", "★ 3"], ["1/2", "▶️"]]

    await harness.press(FavoritesPageCallback(page=1).pack())
    assert "Избранное 0" in harness.last_text()


async def test_favorites_hide_deleted_listings(harness: BotHarness) -> None:
    vake = harness.store.add_district("Ваке")
    await harness.send("/start")
    listing = harness.store.add_listing(vake, is_deleted=True)
    harness.store.favorites.append((harness.user.id, listing.id))

    await harness.send("/favorites")

    assert "пока пусто" in harness.last_text()


# --------------------------------------------------------------------------- profile


async def test_profile(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.user.subscription_expires_at = datetime(2026, 12, 31, tzinfo=UTC)

    await harness.send("👤 Профиль")

    text = harness.last_text()
    assert "Язык: Русский" in text
    assert "Подписка: Бесплатная (до 31.12.2026)" in text
    assert "С нами с 01.09.2026" in text
    assert buttons(harness.last_markup()) == [["✅ Русский", "English", "ქართული"]]


async def test_change_language(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.reset()

    await harness.press(LanguageCallback(code="en").pack())

    assert harness.user.language == "en"
    [edit] = harness.telegram.of(EditMessageText)
    assert "Language: English" in edit.text
    [menu] = harness.telegram.of(SendMessage)
    assert isinstance(menu.reply_markup, ReplyKeyboardMarkup)
    assert menu.reply_markup.keyboard[0][0].text == "🔍 Search"


async def test_forged_language_is_rejected(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.reset()

    await harness.press(LanguageCallback(code="xx").pack())

    assert harness.user.language == "ru"
    [answer] = harness.telegram.of(AnswerCallbackQuery)
    assert answer.show_alert is True


async def test_same_language_does_nothing(harness: BotHarness) -> None:
    await harness.send("/start")
    harness.reset()

    await harness.press(LanguageCallback(code="ru").pack())

    assert [type(call) for call in harness.telegram.calls] == [AnswerCallbackQuery]


# --------------------------------------------------------------------------- robustness


async def test_error_rolls_back_and_notifies_user(
    harness: BotHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    await harness.send("/start", language_code="en")
    monkeypatch.setattr(SearchListingsUseCase, "execute", boom)
    harness.reset()

    await harness.press(SearchCallback(step=SearchStep.RESULTS).pack())

    session = harness.sessions[-1]
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    [answer] = harness.telegram.of(AnswerCallbackQuery)
    assert answer.show_alert is True
    assert answer.text == "⚠️ Something went wrong. Please try again a bit later."


async def test_not_modified_edit_is_ignored(harness: BotHarness) -> None:
    harness.store.add_district("Ваке")
    harness.telegram.fail_edit_with = "Bad Request: message is not modified"

    await harness.press(SearchCallback(step=SearchStep.DISTRICT).pack())

    assert harness.sessions[-1].commit.await_count == 1
    [answer] = harness.telegram.of(AnswerCallbackQuery)
    assert not answer.show_alert


async def test_other_edit_errors_are_reported(harness: BotHarness) -> None:
    harness.store.add_district("Ваке")
    harness.telegram.fail_edit_with = "Bad Request: something else"

    await harness.press(SearchCallback(step=SearchStep.DISTRICT).pack())

    harness.sessions[-1].rollback.assert_awaited_once()
    [answer] = harness.telegram.of(AnswerCallbackQuery)
    assert answer.show_alert is True


async def test_outdated_message_asks_to_reopen(harness: BotHarness) -> None:
    harness.store.add_district("Ваке")
    old = InaccessibleMessage(chat=Chat(id=777, type="private"), message_id=1)

    await harness.press(SearchCallback(step=SearchStep.DISTRICT).pack(), message=old)

    assert harness.telegram.of(EditMessageText) == []
    [answer] = harness.telegram.of(AnswerCallbackQuery)
    assert "устарело" in (answer.text or "")


async def test_updates_from_bots_are_ignored(harness: BotHarness) -> None:
    await harness.send("/start", is_bot=True)

    assert harness.telegram.calls == []
    assert harness.store.users == {}
