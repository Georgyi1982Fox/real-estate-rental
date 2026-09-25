from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bina.application.dtos.pagination import Page
from bina.infrastructure.bot.keyboards.callbacks import (
    FavoritesPageCallback,
    FavoriteToggleCallback,
    SearchCallback,
    SearchStep,
)
from bina.infrastructure.bot.keyboards.favorites import favorites_keyboard
from bina.infrastructure.bot.keyboards.filters import (
    PRICE_RANGES,
    ROOM_OPTIONS,
    filters_from_callback,
    price_label,
    rooms_label,
)
from bina.infrastructure.bot.keyboards.listings import flip_favorite_button
from bina.infrastructure.bot.keyboards.profile import language_keyboard
from bina.infrastructure.bot.keyboards.search import (
    DISTRICTS_PER_PAGE,
    district_keyboard,
    price_keyboard,
    results_keyboard,
)
from bina.infrastructure.db.models import District, Listing

MAX_CALLBACK_BYTES = 64


def texts(markup: InlineKeyboardMarkup) -> list[list[str]]:
    return [[button.text for button in row] for row in markup.inline_keyboard]


def callbacks(markup: InlineKeyboardMarkup) -> list[str]:
    return [b.callback_data for row in markup.inline_keyboard for b in row if b.callback_data]


def make_listings(n: int) -> list[Listing]:
    return [Listing(id=uuid4()) for _ in range(n)]


# --------------------------------------------------------------------------- callback data


def test_largest_search_callback_fits_telegram_limit() -> None:
    packed = SearchCallback(
        step=SearchStep.RESULTS,
        district=UUID(int=2**128 - 1),
        price=len(PRICE_RANGES) - 1,
        rooms=len(ROOM_OPTIONS) - 1,
        page=99999,
    ).pack()
    assert len(packed.encode()) <= MAX_CALLBACK_BYTES


def test_favorite_callback_fits_telegram_limit() -> None:
    packed = FavoriteToggleCallback(listing_id=uuid4()).pack()
    assert len(packed.encode()) <= MAX_CALLBACK_BYTES


def test_search_callback_roundtrip_with_empty_fields() -> None:
    original = SearchCallback(step=SearchStep.ROOMS, district=None, price=2)
    assert SearchCallback.unpack(original.pack()) == original


# --------------------------------------------------------------------------- filters


def test_filters_from_callback() -> None:
    district = uuid4()
    filters = filters_from_callback(
        SearchCallback(step=SearchStep.RESULTS, district=district, price=1, rooms=3)
    )
    assert filters.district_id == district
    assert (filters.price_min, filters.price_max) == (Decimal(1000), Decimal(1500))
    assert (filters.rooms_min, filters.rooms_max) == (4, None)


@pytest.mark.parametrize("index", [None, -1, 99])
def test_unknown_preset_means_any(index: int | None) -> None:
    filters = filters_from_callback(
        SearchCallback(step=SearchStep.RESULTS, price=index, rooms=index)
    )
    assert filters.price_min is None and filters.price_max is None
    assert filters.rooms_min is None and filters.rooms_max is None


@pytest.mark.parametrize(
    ("index", "expected"),
    [(0, "до 1 000 ₾"), (2, "1 500–2 500 ₾"), (4, "от 4 000 ₾"), (None, "Любая цена")],  # noqa: RUF001
)
def test_price_label(index: int | None, expected: str) -> None:
    assert price_label(index, "ru") == expected


@pytest.mark.parametrize(
    ("index", "expected"),
    [(0, "1 rooms"), (3, "4+ rooms"), (None, "Any")],
)
def test_rooms_label(index: int | None, expected: str) -> None:
    assert rooms_label(index, "en") == expected


# --------------------------------------------------------------------------- search keyboards


def test_district_keyboard_paginates() -> None:
    districts = [District(id=uuid4(), name_ru=f"Р{i:02}") for i in range(DISTRICTS_PER_PAGE + 3)]

    first = district_keyboard(districts, 0, "ru")
    assert texts(first)[0] == ["🌍 Любой район"]
    assert texts(first)[-1] == ["▶️"]
    assert sum(len(row) for row in texts(first)[1:-1]) == DISTRICTS_PER_PAGE

    last = district_keyboard(districts, 1, "ru")
    assert texts(last)[-1] == ["◀️"]
    assert texts(last)[1] == ["Р12", "Р13"]


def test_district_keyboard_clamps_page() -> None:
    districts = [District(id=uuid4(), name_ru="Ваке")]
    assert texts(district_keyboard(districts, 5, "ru")) == [["🌍 Любой район"], ["Ваке"]]


def test_district_button_carries_district_to_price_step() -> None:
    district = District(id=uuid4(), name_ru="Ваке")
    data = callbacks(district_keyboard([district], 0, "ru"))[1]
    expected = SearchCallback(step=SearchStep.PRICE, district=district.id)
    assert SearchCallback.unpack(data) == expected


def test_price_keyboard_keeps_district() -> None:
    district = uuid4()
    for data in callbacks(price_keyboard(district, "ru"))[:-1]:  # последняя кнопка «Назад»
        assert SearchCallback.unpack(data).district == district


def test_results_keyboard_middle_page() -> None:
    page = Page(items=make_listings(3), total=9, page=1, page_size=3)
    query = SearchCallback(step=SearchStep.RESULTS, price=2, page=1)
    favorite = page.items[1].id

    markup = results_keyboard(page, query, {favorite}, "ru")

    assert texts(markup) == [["☆ 4", "★ 5", "☆ 6"], ["◀️", "2/3", "▶️"], ["🔄 Новый поиск"]]
    prev_cb = SearchCallback.unpack(markup.inline_keyboard[1][0].callback_data or "")
    next_cb = SearchCallback.unpack(markup.inline_keyboard[1][2].callback_data or "")
    assert (prev_cb.page, prev_cb.price) == (0, 2)
    assert (next_cb.page, next_cb.price) == (2, 2)


def test_results_keyboard_single_page_has_no_navigation() -> None:
    page = Page(items=make_listings(2), total=2, page=0, page_size=3)
    markup = results_keyboard(page, SearchCallback(step=SearchStep.RESULTS), set(), "en")
    assert texts(markup) == [["☆ 1", "☆ 2"], ["🔄 New search"]]


# --------------------------------------------------------------------------- favorites, profile


def test_favorites_keyboard() -> None:
    page = Page(items=make_listings(1), total=4, page=3, page_size=1)
    markup = favorites_keyboard(page, "ru", mini_app_url="https://app")

    assert texts(markup)[:2] == [["★ 4"], ["◀️", "4/4"]]
    prev_data = markup.inline_keyboard[1][0].callback_data or ""
    assert FavoritesPageCallback.unpack(prev_data).page == 2
    assert markup.inline_keyboard[-1][0].web_app is not None


def test_flip_favorite_button_changes_only_target() -> None:
    target = FavoriteToggleCallback(listing_id=uuid4()).pack()
    other = FavoriteToggleCallback(listing_id=uuid4()).pack()
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="☆ 1", callback_data=other),
                InlineKeyboardButton(text="☆ 2", callback_data=target),
            ],
            [InlineKeyboardButton(text="🔄", callback_data="x")],
        ]
    )

    flipped = flip_favorite_button(markup, target, is_favorite=True)

    assert texts(flipped) == [["☆ 1", "★ 2"], ["🔄"]]
    assert texts(markup) == [["☆ 1", "☆ 2"], ["🔄"]], "исходная клавиатура не меняется"
    assert texts(flip_favorite_button(flipped, target, is_favorite=False))[0] == ["☆ 1", "☆ 2"]


def test_language_keyboard_marks_current() -> None:
    assert texts(language_keyboard("ka")) == [["Русский", "English", "✅ ქართული"]]
