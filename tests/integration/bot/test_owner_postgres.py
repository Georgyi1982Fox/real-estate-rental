"""Собственник размещает квартиру в боте (TASK-096), на настоящем PostgreSQL."""

import asyncio
import io
from datetime import UTC, datetime
from decimal import Decimal
from itertools import count
from pathlib import Path
from typing import Any

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import SendMessage
from aiogram.types import (
    CallbackQuery,
    Chat,
    Contact,
    InlineKeyboardMarkup,
    Location,
    Message,
    PhotoSize,
    Update,
)
from aiogram.types import User as TelegramUser
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.infrastructure.bot.factory import create_dispatcher
from bina.infrastructure.bot.handlers import owner as owner_handlers
from bina.infrastructure.bot.keyboards.callbacks import (
    AdminAction,
    AdminCallback,
    OwnerAction,
    OwnerCallback,
)
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.db.models import Listing, ListingStatus
from bina.infrastructure.db.repositories.listings import ListingsRepository
from tests.support.telegram import BOT_USERNAME, CHAT_ID, TOKEN, FakeTelegramSession

ADMIN_ID = 555
CHAT = Chat(id=CHAT_ID, type="private")


def jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (2000, 1500), (10, 120, 200)).save(out, "JPEG")
    return out.getvalue()


class Owner:
    """Собственник пишет боту: текст, фото, контакт, кнопки."""

    def __init__(self, dispatcher: Dispatcher, bot: Bot, username: str | None) -> None:
        self.dispatcher = dispatcher
        self.bot = bot
        self.user = TelegramUser(
            id=CHAT_ID, is_bot=False, first_name="Nino", language_code="ru", username=username
        )
        self._ids = count(1)

    async def _message(self, **content: Any) -> None:
        message = Message(
            message_id=next(self._ids),
            date=datetime.now(UTC),
            chat=CHAT,
            from_user=self.user,
            **content,
        )
        await self.dispatcher.feed_update(
            self.bot, Update(update_id=next(self._ids), message=message)
        )

    async def send(self, text: str) -> None:
        await self._message(text=text)

    async def photo(self, file_id: str) -> None:
        size = PhotoSize(file_id=file_id, file_unique_id=file_id, width=1280, height=960)
        await self._message(photo=[size])

    async def contact(self, phone: str) -> None:
        await self._message(contact=Contact(phone_number=phone, first_name="Nino", user_id=CHAT_ID))

    async def press(self, data: str, markup: InlineKeyboardMarkup | None = None) -> None:
        message = Message(
            message_id=1, date=datetime.now(UTC), chat=CHAT, text="…", reply_markup=markup
        )
        query = CallbackQuery(
            id=str(next(self._ids)),
            from_user=self.user,
            chat_instance="ci",
            data=data,
            message=message,
        )
        await self.dispatcher.feed_update(
            self.bot, Update(update_id=next(self._ids), callback_query=query)
        )


@pytest.fixture
def telegram() -> FakeTelegramSession:
    return FakeTelegramSession()


@pytest.fixture
def media(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))

    async def download(bot: Bot, file_ids: list[str]) -> list[bytes]:
        return [jpeg() for _ in file_ids]

    monkeypatch.setattr(owner_handlers, "download_photos", download)
    return tmp_path


def make_owner(
    session_factory: async_sessionmaker[AsyncSession],
    telegram: FakeTelegramSession,
    username: str | None = "nino_home",
) -> Owner:
    # Мастер — много сообщений подряд; защиту от флуда проверяют отдельные тесты
    settings = BotSettings(token=TOKEN, admin_ids=(ADMIN_ID,), rate_limit=100)
    dispatcher = create_dispatcher(settings, session_factory)
    return Owner(dispatcher, Bot(token=TOKEN, session=telegram), username)


def texts(telegram: FakeTelegramSession) -> list[str]:
    return [call.text for call in telegram.of(SendMessage)]


async def walk_to_photos(owner: Owner) -> None:
    await owner.send("🏠 Сдать квартиру")
    await owner.press(OwnerCallback(action=OwnerAction.NEW).pack())
    await owner.press(OwnerCallback(action=OwnerAction.CITY, value="tbilisi").pack())
    await owner.send("Ваке")
    await owner.send("ул. Чавчавадзе, 10")
    await owner.press(OwnerCallback(action=OwnerAction.PERIOD, value="monthly").pack())
    await owner.press(OwnerCallback(action=OwnerAction.ROOMS, value="2").pack())
    await owner.send("5")  # слишком маленькая площадь — переспросит
    await owner.send("60")
    await owner.send("1500")
    await owner.send("5/9")
    await owner.send("Коротко")  # слишком короткое описание — переспросит
    await owner.send("Светлая квартира с новым ремонтом, рядом парк Ваке и метро.")


async def test_owner_posts_apartment(
    session_factory: async_sessionmaker[AsyncSession],
    session: AsyncSession,
    telegram: FakeTelegramSession,
    media: Path,
) -> None:
    owner = make_owner(session_factory, telegram)
    await walk_to_photos(owner)
    sent = texts(telegram)
    assert any("Площадь в м²" in text for text in sent)
    assert any("от 10 до 1000" in text for text in sent)
    assert any("от 20 до 3000" in text for text in sent)

    await owner.press(OwnerCallback(action=OwnerAction.PHOTOS_DONE).pack())  # ещё нет фото
    await owner.photo("p1")
    await owner.photo("p2")
    assert "Фото 2/10" in texts(telegram)[-1]
    await owner.press(OwnerCallback(action=OwnerAction.PHOTOS_DONE).pack())
    await owner.contact("+995 555 12 34 56")
    assert "Проверьте объявление" in texts(telegram)[-1]
    assert "+995555123456" in texts(telegram)[-1]

    await owner.press(OwnerCallback(action=OwnerAction.PUBLISH).pack())

    published = next(text for text in texts(telegram) if "опубликовано" in text)
    assert "2-комн. квартира, Ваке, 60 м²" in published
    admin_alert = next(call for call in telegram.of(SendMessage) if call.chat_id == ADMIN_ID)
    assert "Новое объявление собственника" in admin_alert.text
    hide = admin_alert.reply_markup.inline_keyboard[0][0].callback_data
    assert AdminCallback.unpack(hide).action == AdminAction.HIDE

    listing = (await session.execute(select(Listing))).scalar_one()
    assert (listing.source_name, listing.owner_type, listing.rent_period) == (
        "owner",
        "owner",
        "monthly",
    )
    assert (listing.floor, listing.total_floors, listing.phone) == (5, 9, "+995555123456")
    assert listing.address == "ул. Чавчавадзе, 10", "точку найдёт шаг geocode"
    assert any("Где именно квартира" in text for text in sent)
    assert listing.url == f"https://t.me/{BOT_USERNAME}?start=chat_{listing.id}"
    assert (listing.title_ru, listing.title_en) == (
        "2-комн. квартира, Ваке, 60 м²",
        "2-room apartment, Vake, 60 m²",
    )
    assert listing.description_ru.startswith("Светлая квартира")
    assert listing.owner_user_id is not None
    assert len(listing.images) == 2
    saved = [media / url.removeprefix("/api/media/") for url in listing.images]
    assert all(path.is_file() for path in saved)
    with Image.open(saved[0]) as image:
        assert max(image.size) == 1600, "фото уменьшено"

    found = await ListingsRepository(session).search(ListingSearchFilters(), limit=10)
    assert [item.id for item in found] == [listing.id], "сразу в поиске"


async def test_take_down_and_change_price(
    session_factory: async_sessionmaker[AsyncSession],
    session: AsyncSession,
    telegram: FakeTelegramSession,
    media: Path,
) -> None:
    owner = make_owner(session_factory, telegram)
    await walk_to_photos(owner)
    await owner.photo("p1")
    await owner.press(OwnerCallback(action=OwnerAction.PHOTOS_DONE).pack())
    await owner.send("✉️ Только через Telegram")
    await owner.press(OwnerCallback(action=OwnerAction.PUBLISH).pack())
    listing = (await session.execute(select(Listing))).scalar_one()
    assert listing.phone is None

    await owner.send("/mylistings")
    assert "🟢 в поиске" in texts(telegram)[-1]

    await owner.press(OwnerCallback(action=OwnerAction.PRICE, listing=listing.id).pack())
    await owner.send("1300")
    assert "Новая цена: 1 300 ₾" in texts(telegram)[-1]

    await owner.press(OwnerCallback(action=OwnerAction.OFF, listing=listing.id).pack())
    assert "⚪ снято" in texts(telegram)[-1]

    await session.refresh(listing)
    assert listing.status == ListingStatus.ARCHIVED
    assert (listing.price, listing.previous_price) == (Decimal(1300), Decimal(1500))


async def test_no_username_needs_phone(
    session_factory: async_sessionmaker[AsyncSession],
    telegram: FakeTelegramSession,
    media: Path,
) -> None:
    owner = make_owner(session_factory, telegram, username=None)
    await walk_to_photos(owner)
    await owner.photo("p1")
    await owner.press(OwnerCallback(action=OwnerAction.PHOTOS_DONE).pack())
    await owner.send("✉️ Только через Telegram")
    assert "Не похоже на телефон" in texts(telegram)[-1]
    await owner.send("555 12 34 56")
    assert "Проверьте объявление" in texts(telegram)[-1]


async def test_menu_button_during_wizard_is_not_an_answer(
    session_factory: async_sessionmaker[AsyncSession],
    telegram: FakeTelegramSession,
    media: Path,
) -> None:
    owner = make_owner(session_factory, telegram)
    await owner.press(OwnerCallback(action=OwnerAction.NEW).pack())
    await owner.press(OwnerCallback(action=OwnerAction.CITY, value="tbilisi").pack())
    await owner.send("🔍 Поиск")
    # Кнопка меню открыла поиск, а не стала названием района
    assert "Напишите название района" not in texts(telegram)[-1]
    assert not any("Как сдаёте" in text for text in texts(telegram))


async def test_album_photos_arrive_together(
    session_factory: async_sessionmaker[AsyncSession],
    telegram: FakeTelegramSession,
    media: Path,
) -> None:
    """Альбом: фото обрабатываются одновременно — ни одно не теряется."""
    owner = make_owner(session_factory, telegram)
    await walk_to_photos(owner)
    await asyncio.gather(*(owner.photo(f"p{n}") for n in range(4)))
    assert any("Фото 4/10" in text for text in texts(telegram))


async def test_location_point_and_skip(
    session_factory: async_sessionmaker[AsyncSession],
    telegram: FakeTelegramSession,
) -> None:
    owner = make_owner(session_factory, telegram)
    await owner.send("🏠 Сдать квартиру")
    await owner.press(OwnerCallback(action=OwnerAction.NEW).pack())
    await owner.press(OwnerCallback(action=OwnerAction.CITY, value="tbilisi").pack())
    await owner.send("Ваке")
    await owner.send("ул")  # слишком короткий адрес — переспросит
    assert "улицу и номер дома" in texts(telegram)[-1]
    await owner._message(location=Location(latitude=48.85, longitude=2.35))  # Париж
    assert "не в Грузии" in texts(telegram)[-1]
    await owner._message(location=Location(latitude=41.7105, longitude=44.7590))
    assert "Как сдаёте" in texts(telegram)[-1]
    state = await owner.dispatcher.fsm.get_context(owner.bot, CHAT_ID, CHAT_ID).get_data()
    assert (state["latitude"], state["longitude"]) == (41.7105, 44.759)

    # Пропустить тоже можно
    await owner.press(OwnerCallback(action=OwnerAction.NEW).pack())
    await owner.press(OwnerCallback(action=OwnerAction.CITY, value="tbilisi").pack())
    await owner.send("Сабуртало")
    await owner.press(OwnerCallback(action=OwnerAction.SKIP_LOCATION).pack())
    assert "Как сдаёте" in texts(telegram)[-1]
