"""Гостиницы в боте и «🔥 Топ» за звёзды (TASK-120, этап 2), на PostgreSQL."""

from datetime import UTC, datetime, timedelta

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerCallbackQuery, AnswerPreCheckoutQuery, SendMessage, SendPhoto
from aiogram.types import InlineKeyboardMarkup, SuccessfulPayment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.hotel_promotion import hotel_promotion_payload
from bina.application.hotels import HotelDraft, RoomDraft
from bina.application.ports.translator import IMessageTranslator
from bina.infrastructure.bot.factory import create_dispatcher
from bina.infrastructure.bot.keyboards.callbacks import (
    ChatAction,
    ChatCallback,
    HotelAction,
    HotelCallback,
    MenuCallback,
    MenuSection,
)
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.db.models import ChatMessage, Conversation, Hotel, Payment, User
from bina.infrastructure.db.repositories.hotels import HotelsRepository
from tests.support.people import Person
from tests.support.telegram import BOT_USERNAME, TOKEN, FakeTelegramSession

OWNER_ID = 3003
GUEST_ID = 3004
MINI_APP = "https://app.example"


@pytest.fixture
def telegram() -> FakeTelegramSession:
    return FakeTelegramSession()


class EchoTranslator(IMessageTranslator):
    """Перевод — пометка языка перед текстом."""

    async def translate_message(self, text: str, target: str) -> str:
        return f"[{target}] {text}"


@pytest.fixture
def dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    return create_dispatcher(
        BotSettings(token=TOKEN, mini_app_url=MINI_APP),
        session_factory,
        message_translator=EchoTranslator(),
    )


@pytest.fixture
async def people(dispatcher: Dispatcher, telegram: FakeTelegramSession) -> dict[str, Person]:
    bot = Bot(token=TOKEN, session=telegram)
    people = {
        "owner": Person(dispatcher, bot, OWNER_ID, "ru"),
        "guest": Person(dispatcher, bot, GUEST_ID, "en"),
    }
    for person in people.values():
        await person.send("/start")
    telegram.calls.clear()
    return people


def draft(name: str, **changes: object) -> HotelDraft:
    fields: dict[str, object] = {
        "kind": "guesthouse",
        "name": name,
        "city": "batumi",
        "description": "Уютный гостевой дом в пяти минутах от моря, с садом и террасой.",
        "address": "ул. Химшиашвили, 10",
        "stars": 3,
        "check_in": "14:00",
        "check_out": "12:00",
        "phone": "+995599112233",
        "whatsapp": "+995599112233",
        "rooms": (RoomDraft(kind="double", guests=2, price=120),),
        **changes,
    }
    return HotelDraft(**fields)  # type: ignore[arg-type]


async def add_hotel(
    session_factory: async_sessionmaker[AsyncSession], name: str, age_days: int = 0
) -> Hotel:
    async with session_factory() as session:
        owner = (
            await session.execute(select(User).where(User.telegram_id == OWNER_ID))
        ).scalar_one()
        hotel = await HotelsRepository(session).create(owner.id, draft(name))
        hotel.created_at = datetime.now(UTC) - timedelta(days=age_days)
        await session.commit()
        return hotel


def last_markup(telegram: FakeTelegramSession) -> InlineKeyboardMarkup:
    markup = telegram.of(SendMessage)[-1].reply_markup
    assert isinstance(markup, InlineKeyboardMarkup)
    return markup


def buttons(markup: InlineKeyboardMarkup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


async def test_hotels_section_card_and_contacts(
    people: dict[str, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    guest = people["guest"]
    await guest.press(MenuCallback(section=MenuSection.HOTELS).pack())
    assert "There are no properties here yet" in (telegram.of(SendMessage)[-1].text or "")

    hotel = await add_hotel(session_factory, "Sea Breeze")
    telegram.calls.clear()
    await guest.send("/hotels")
    [section] = telegram.of(SendMessage)
    assert "Hotels, guest houses and hostels" in (section.text or "")
    markup = last_markup(telegram)
    assert buttons(markup) == [
        "Sea Breeze · Batumi · from 120 ₾",
        "📱 All hotels",
        "🏨 My hotels",
        "🏠 Main menu",
    ]
    assert markup.inline_keyboard[1][0].web_app is not None
    assert markup.inline_keyboard[1][0].web_app.url == f"{MINI_APP}/hotels"

    # Кнопка объекта — карточка (без фото — текстом), всё по-английски
    telegram.calls.clear()
    await guest.press(markup.inline_keyboard[0][0].callback_data or "")
    card = telegram.of(SendMessage)[-1]
    text = card.text or ""
    assert "Sea Breeze</b> ⭐⭐⭐" in text
    assert "Guest house · 📍 Batumi" in text
    assert "from 120 ₾ per night · 👥 up to 2 guests" in text
    assert "Check-in from 14:00, check-out until 12:00" in text
    assert "+995" not in text, "телефон — только по кнопке «Контакты»"
    card_markup = last_markup(telegram)
    assert buttons(card_markup) == [
        "✍️ Message the owner",
        "📞 Contacts",
        "📱 More in the app",
        "📤 Share",
        "🏠 Main menu",
    ]
    share = card_markup.inline_keyboard[3][0].url or ""
    assert f"start%3Dh_{hotel.id.hex}" in share and BOT_USERNAME in share

    telegram.calls.clear()
    await guest.press(card_markup.inline_keyboard[1][0].callback_data or "")
    contacts = telegram.of(SendMessage)[-1]
    assert "+995599112233" in (contacts.text or "")
    urls = [b.url for row in last_markup(telegram).inline_keyboard for b in row if b.url]
    assert urls == ["https://wa.me/995599112233"]

    # Ссылка «Поделиться» открывает ту же карточку
    telegram.calls.clear()
    await guest.send(f"/start h_{hotel.id.hex}")
    assert any("Sea Breeze" in (call.text or "") for call in telegram.of(SendMessage))


async def test_hotel_card_with_photo_and_hidden_hotel(
    people: dict[str, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = people["owner"]
    hotel = await add_hotel(session_factory, "Гостевой дом Нино")
    async with session_factory() as session:
        stored = await session.get(Hotel, hotel.id)
        assert stored is not None
        stored.images = ["/api/media/hotels/1.jpg"]
        await session.commit()

    await owner.press(HotelCallback(action=HotelAction.OPEN, id=hotel.id).pack())
    [photo] = telegram.of(SendPhoto)
    assert photo.photo == f"{MINI_APP}/api/media/hotels/1.jpg"
    assert "Гостевой дом · 📍 Батуми" in (photo.caption or "")

    async with session_factory() as session:
        await HotelsRepository(session).hide(hotel.id)
        await session.commit()
    await owner.press(HotelCallback(action=HotelAction.CONTACTS, id=hotel.id).pack())
    assert "больше недоступен" in (telegram.of(AnswerCallbackQuery)[-1].text or "")
    await owner.send(f"/start h_{hotel.id.hex}")
    assert "больше недоступен" in (telegram.of(SendMessage)[-1].text or "")


def last_to(telegram: FakeTelegramSession, chat_id: int) -> SendMessage:
    sent: SendMessage = [call for call in telegram.of(SendMessage) if call.chat_id == chat_id][-1]
    return sent


def callbacks(message: SendMessage) -> list[str]:
    assert isinstance(message.reply_markup, InlineKeyboardMarkup)
    return [b.callback_data or "" for row in message.reply_markup.inline_keyboard for b in row]


async def test_chat_with_hotel_owner(
    people: dict[str, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Этап 2: гость пишет хозяину гостиницы через бота, оба — на своём языке."""
    owner, guest = people["owner"], people["guest"]
    hotel = await add_hotel(session_factory, "Sea Breeze")
    write = HotelCallback(action=HotelAction.WRITE, id=hotel.id).pack()

    await guest.press(write)
    assert "Write to the hotel owner" in (last_to(telegram, GUEST_ID).text or "")
    await guest.send("Hello! Is a double room free on 1 May?")

    to_owner = last_to(telegram, OWNER_ID)
    text = to_owner.text or ""
    assert "Сообщение от гостя</b>\n🏨 Sea Breeze" in text
    assert "[ru] Hello! Is a double room free on 1 May?" in text
    assert "Оригинал: Hello!" in text
    assert str(GUEST_ID) not in text, "Telegram гостя не виден"
    assert "Sent" in (last_to(telegram, GUEST_ID).text or "")

    [reply] = callbacks(to_owner)
    assert ChatCallback.unpack(reply).action == ChatAction.REPLY
    await owner.press(reply)
    await owner.send("Да, свободен. Завтрак включён.")
    to_guest = last_to(telegram, GUEST_ID)
    assert "Reply from the hotel</b>\n🏨 Sea Breeze" in (to_guest.text or "")
    assert "[en] Да, свободен. Завтрак включён." in (to_guest.text or "")
    # Гостю — «Ответить» и снова карточка гостиницы (просмотров у гостиниц нет)
    assert callbacks(to_guest)[1] == HotelCallback(action=HotelAction.OPEN, id=hotel.id).pack()
    assert len(callbacks(to_guest)) == 2

    # Повторное «Написать» — тот же диалог
    await guest.press(write)
    await guest.send("Thanks!")
    async with session_factory() as session:
        [conversation] = (await session.execute(select(Conversation))).scalars().all()
        assert conversation.hotel_id == hotel.id and conversation.listing_id is None
        stored = (await session.execute(select(ChatMessage))).scalars().all()
        assert len(stored) == 3

    # Своей гостинице не пишут: в карточке нет кнопки, нажатие — подсказка
    telegram.calls.clear()
    await owner.press(HotelCallback(action=HotelAction.OPEN, id=hotel.id).pack())
    assert write not in callbacks(last_to(telegram, OWNER_ID))
    await owner.press(write)
    assert "Это ваша гостиница" in (telegram.of(AnswerCallbackQuery)[-1].text or "")


async def pay(person: Person, payload: str, charge_id: str, amount: int = 150) -> None:
    await person.message(
        successful_payment=SuccessfulPayment(
            currency="XTR",
            total_amount=amount,
            invoice_payload=payload,
            telegram_payment_charge_id=charge_id,
            provider_payment_charge_id="",
        )
    )


async def test_hotel_promotion_paid_with_stars(
    people: dict[str, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner, guest = people["owner"], people["guest"]
    promoted = await add_hotel(session_factory, "Old Hotel", age_days=3)
    newer = await add_hotel(session_factory, "New Hotel")
    payload = hotel_promotion_payload(promoted.id)

    await owner.pre_checkout(payload, 100)  # не та сумма
    await guest.pre_checkout(payload, 150)  # чужой объект
    await owner.pre_checkout(payload, 150)
    assert [answer.ok for answer in telegram.of(AnswerPreCheckoutQuery)] == [False, False, True]

    await pay(owner, payload, "hotel-charge-1")
    activated = telegram.of(SendMessage)[-1]
    assert "«Old Hotel» в топе раздела «Гостиницы» до" in (activated.text or "")
    assert isinstance(activated.reply_markup, InlineKeyboardMarkup)
    assert "🏨 Мои гостиницы" in buttons(activated.reply_markup)
    await pay(owner, payload, "hotel-charge-1")  # Telegram прислал повторно

    async with session_factory() as session:
        stored = await session.get(Hotel, promoted.id)
        assert stored is not None and stored.promoted_until is not None
        days = (stored.promoted_until - datetime.now(UTC)).total_seconds() / 86400
        assert 6.9 < days <= 7, "повтор не продлевает"
        payments = (await session.execute(select(Payment))).scalars().all()
        assert [(p.plan, int(p.amount)) for p in payments] == [("hotel_promo", 150)]

    # В разделе — первым и со значком, хотя есть объект новее
    telegram.calls.clear()
    await guest.send("/hotels")
    assert buttons(last_markup(telegram))[:2] == [
        "🔥 Old Hotel · Batumi · from 120 ₾",
        "New Hotel · Batumi · from 120 ₾",
    ]
    assert newer.promoted_until is None

    # Снятый с показа объект не продвигается
    async with session_factory() as session:
        stored = await session.get(Hotel, newer.id)
        assert stored is not None
        stored.is_active = False
        await session.commit()
    await owner.pre_checkout(hotel_promotion_payload(newer.id), 150)
    answer = telegram.of(AnswerPreCheckoutQuery)[-1]
    assert answer.ok is False and "Мои гостиницы" in (answer.error_message or "")
