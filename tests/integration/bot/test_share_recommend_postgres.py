"""Бот: карточка по ссылке «Поделиться» и «Вам может понравиться» (TASK-073, TASK-076)."""

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import SendMessage, SendPhoto
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.infrastructure.bot.factory import create_dispatcher
from bina.infrastructure.bot.keyboards.callbacks import FavoriteToggleCallback, RecommendCallback
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.people import Person
from tests.support.telegram import BOT_USERNAME, TOKEN, FakeTelegramSession

USER_ID = 7302
APP = "https://bina.example"


@pytest.fixture
def telegram() -> FakeTelegramSession:
    return FakeTelegramSession()


@pytest.fixture
def dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    return create_dispatcher(
        BotSettings(token=TOKEN, mini_app_url=APP, rate_limit=100), session_factory
    )


@pytest.fixture
async def person(dispatcher: Dispatcher, telegram: FakeTelegramSession) -> Person:
    person = Person(dispatcher, Bot(token=TOKEN, session=telegram), USER_ID, "ru")
    await person.send("/start")
    return person


async def add(
    factory: async_sessionmaker[AsyncSession],
    source_id: str,
    rooms: int,
    price: int,
    images: list[str] | None = None,
) -> Listing:
    async with factory() as session:
        listing = await ListingsRepository(session).create_or_update_from_raw(
            RawListing(
                source_id=source_id,
                source_name="ss",
                title="Квартира",
                description="",
                price=float(price),
                currency="GEL",
                rooms=rooms,
                area=60,
                district="Ваке",
                url=f"https://ss.example/{source_id}",
                photos=images or [],
            )
        )
        await session.commit()
        return listing


def buttons(markup: object) -> list[str]:
    assert isinstance(markup, InlineKeyboardMarkup)
    return [button.text for row in markup.inline_keyboard for button in row]


async def test_shared_link_opens_card_with_photo(
    person: Person,
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    listing = await add(session_factory, "p1", 2, 1500, ["https://img.example/1.jpg"])
    telegram.calls.clear()
    await person.send(f"/start l_{listing.id.hex}")

    [photo] = telegram.of(SendPhoto)
    assert photo.photo == "https://img.example/1.jpg"
    assert "1 500 ₾" in (photo.caption or "") and "Ваке" in (photo.caption or "")
    labels = buttons(photo.reply_markup)
    assert "☆ В избранное" in labels and "📤 Поделиться" in labels
    assert "🌐 Открыть на сайте" in labels and "📱 Подробнее в приложении" in labels
    assert isinstance(photo.reply_markup, InlineKeyboardMarkup)
    share = next(
        b for row in photo.reply_markup.inline_keyboard for b in row if b.text == "📤 Поделиться"
    )
    assert f"start%3Dl_{listing.id.hex}" in (share.url or "") and BOT_USERNAME in (share.url or "")

    await person.send("/start l_00000000000000000000000000000000")
    assert "больше недоступно" in (telegram.of(SendMessage)[-1].text or "")


async def test_you_may_like_from_favorites(
    person: Person,
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    liked = await add(session_factory, "liked", 2, 1500)
    similar = await add(session_factory, "similar", 2, 1550)
    telegram.calls.clear()
    await person.press(RecommendCallback().pack())
    assert "Добавьте пару квартир в избранное" in (telegram.of(SendMessage)[-1].text or "")

    await person.press(FavoriteToggleCallback(listing_id=liked.id).pack())
    await person.send("❤️ Избранное")
    assert "✨ Вам может понравиться" in buttons(telegram.of(SendMessage)[-1].reply_markup)
    await person.press(RecommendCallback().pack())
    text = telegram.of(SendMessage)[-1].text or ""
    assert "Вам может понравиться" in text and "1 550 ₾" in text
    assert "1 500 ₾" not in text, "избранное не предлагаем"
    assert similar.id


async def test_recently_viewed_and_notes(
    person: Person,
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """TASK-075 / TASK-074: открытая карточка — в «Недавно смотрели», заметка — в избранном."""
    from bina.infrastructure.bot.keyboards.callbacks import HistoryCallback
    from bina.infrastructure.db.repositories.favorites import FavoritesRepository
    from bina.infrastructure.db.repositories.users import UsersRepository

    telegram.calls.clear()
    await person.press(HistoryCallback().pack())
    assert "ещё не открывали" in (telegram.of(SendMessage)[-1].text or "")

    listing = await add(session_factory, "seen", 2, 1700)
    await person.send(f"/start l_{listing.id.hex}")
    await person.press(HistoryCallback().pack())
    text = telegram.of(SendMessage)[-1].text or ""
    assert "Недавно смотрели" in text and "1 700 ₾" in text

    await person.press(FavoriteToggleCallback(listing_id=listing.id).pack())
    async with session_factory() as session:
        user = await UsersRepository(session).get_by_telegram_id(USER_ID)
        assert user is not None
        await FavoritesRepository(session).set_note(user.id, listing.id, "Позвонить <в пятницу>")
        await session.commit()
    await person.send("❤️ Избранное")
    favorites = telegram.of(SendMessage)[-1].text or ""
    assert "Ваши заметки" in favorites and "1. Позвонить &lt;в пятницу&gt;" in favorites
