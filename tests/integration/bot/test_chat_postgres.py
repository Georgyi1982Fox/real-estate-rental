"""Чат с хозяином с переводом и запись на просмотр (TASK-111, TASK-112), на PostgreSQL."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count
from uuid import UUID

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from aiogram.types import CallbackQuery, Chat, InlineKeyboardMarkup, Message, Update
from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.chat import viewing_days, viewing_start
from bina.application.owner_listings import OwnerListingDraft
from bina.application.ports.translator import IMessageTranslator
from bina.infrastructure.bot.factory import create_dispatcher
from bina.infrastructure.bot.keyboards.callbacks import ChatAction, ChatCallback
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.viewing_reminders import send_viewing_reminders
from bina.infrastructure.db.models import ChatMessage, Listing, User, Viewing
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository
from tests.support.telegram import TOKEN, FakeTelegramSession

TENANT_ID = 1001
OWNER_ID = 2002
OTHER_TENANT_ID = 3003


class EchoTranslator(IMessageTranslator):
    """Перевод — пометка языка перед текстом."""

    async def translate_message(self, text: str, target: str) -> str:
        return f"[{target}] {text}"


class Person:
    """Человек пишет боту (арендатор или хозяин)."""

    def __init__(self, dispatcher: Dispatcher, bot: Bot, telegram_id: int, language: str) -> None:
        self.dispatcher = dispatcher
        self.bot = bot
        self.chat = Chat(id=telegram_id, type="private")
        self.user = TelegramUser(
            id=telegram_id, is_bot=False, first_name="User", language_code=language
        )
        self._ids = count(telegram_id * 1000)

    async def send(self, text: str) -> None:
        message = Message(
            message_id=next(self._ids),
            date=datetime.now(UTC),
            chat=self.chat,
            from_user=self.user,
            text=text,
        )
        await self.dispatcher.feed_update(
            self.bot, Update(update_id=next(self._ids), message=message)
        )

    async def press(self, data: str, markup: InlineKeyboardMarkup | None = None) -> None:
        message = Message(
            message_id=1, date=datetime.now(UTC), chat=self.chat, text="…", reply_markup=markup
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
def bot(telegram: FakeTelegramSession) -> Bot:
    return Bot(token=TOKEN, session=telegram)


@pytest.fixture
def dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    return create_dispatcher(
        BotSettings(token=TOKEN), session_factory, message_translator=EchoTranslator()
    )


@pytest.fixture
async def people(dispatcher: Dispatcher, bot: Bot) -> dict[str, Person]:
    people = {
        "tenant": Person(dispatcher, bot, TENANT_ID, "ru"),
        "owner": Person(dispatcher, bot, OWNER_ID, "ka"),
        "other": Person(dispatcher, bot, OTHER_TENANT_ID, "en"),
    }
    for person in people.values():
        await person.send("/start")  # регистрация
    return people


@pytest.fixture
async def listing(
    people: dict[str, Person], session_factory: async_sessionmaker[AsyncSession]
) -> Listing:
    async with session_factory() as session:
        owner = (
            await session.execute(select(User).where(User.telegram_id == OWNER_ID))
        ).scalar_one()
        draft = OwnerListingDraft(
            city="tbilisi",
            district="Ваке",
            rent_period="monthly",
            price=Decimal(1500),
            currency="GEL",
            rooms=2,
            area=Decimal(60),
            description="Светлая квартира с новым ремонтом, рядом парк Ваке.",
            phone="+995555123456",
        )
        listing = await OwnerListingsRepository(session).create(
            owner.id, draft, "chat-test", [], datetime.now(UTC)
        )
        listing.address = "ул. Чавчавадзе, 10"
        await session.commit()
        return listing


def messages_to(telegram: FakeTelegramSession, chat_id: int) -> list[SendMessage]:
    return [call for call in telegram.of(SendMessage) if call.chat_id == chat_id]


def alerts(telegram: FakeTelegramSession) -> list[str]:
    return [call.text or "" for call in telegram.of(AnswerCallbackQuery)]


def button_data(call: SendMessage, action: ChatAction) -> str:
    markup = call.reply_markup
    assert isinstance(markup, InlineKeyboardMarkup)
    for row in markup.inline_keyboard:
        for button in row:
            data = button.callback_data or ""
            if data.startswith("ch:") and ChatCallback.unpack(data).action == action:
                return data
    raise AssertionError(f"no {action} button")


async def test_chat_with_translation(
    people: dict[str, Person],
    listing: Listing,
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    tenant, owner = people["tenant"], people["owner"]
    telegram.calls.clear()

    await tenant.send(f"/start chat_{listing.id}")
    card = messages_to(telegram, TENANT_ID)[-1]
    assert "2-комн. квартира, Ваке, 60 м²" in card.text
    assert "Напишите хозяину" in card.text

    await tenant.press(button_data(card, ChatAction.WRITE))
    assert "Напишите сообщение хозяину" in messages_to(telegram, TENANT_ID)[-1].text
    await tenant.send("Здравствуйте! Квартира свободна?")

    to_owner = messages_to(telegram, OWNER_ID)[-1]
    assert "შეტყობინება დამქირავებლისგან" in to_owner.text
    assert "[ka] Здравствуйте! Квартира свободна?" in to_owner.text
    assert "ორიგინალი: Здравствуйте!" in to_owner.text
    assert str(TENANT_ID) not in to_owner.text, "Telegram арендатора не виден"
    assert "Отправлено" in messages_to(telegram, TENANT_ID)[-1].text

    await owner.press(button_data(to_owner, ChatAction.REPLY))
    await owner.send("კი, თავისუფალია")
    to_tenant = messages_to(telegram, TENANT_ID)[-1]
    assert "Ответ хозяина" in to_tenant.text
    assert "[ru] კი, თავისუფალია" in to_tenant.text
    # Арендатору под ответом — «Ответить» и «Записаться на просмотр»
    button_data(to_tenant, ChatAction.VIEW)

    async with session_factory() as session:
        stored = (
            (await session.execute(select(ChatMessage).order_by(ChatMessage.created_at)))
            .scalars()
            .all()
        )
    assert [(m.text, m.translated_text, m.target_language) for m in stored] == [
        ("Здравствуйте! Квартира свободна?", "[ka] Здравствуйте! Квартира свободна?", "ka"),
        ("კი, თავისუფალია", "[ru] კი, თავისუფალია", "ru"),
    ]


async def test_menu_button_is_not_a_chat_message(
    people: dict[str, Person], listing: Listing, telegram: FakeTelegramSession
) -> None:
    tenant = people["tenant"]
    await tenant.press(ChatCallback(action=ChatAction.WRITE, id=listing.id).pack())
    telegram.calls.clear()
    await tenant.send("🏠 Главное меню")
    assert not messages_to(telegram, OWNER_ID)
    await tenant.send("Это уже не сообщение хозяину")
    assert not messages_to(telegram, OWNER_ID)


async def test_own_listing_and_unknown_listing(
    people: dict[str, Person], listing: Listing, telegram: FakeTelegramSession
) -> None:
    await people["owner"].send(f"/start chat_{listing.id}")
    assert "ეს თქვენი განცხადებაა" in messages_to(telegram, OWNER_ID)[-1].text
    await people["tenant"].send(f"/start chat_{UUID(int=1)}")
    assert "больше недоступно" in messages_to(telegram, TENANT_ID)[-1].text


async def test_viewing_confirmed_and_reminded(
    people: dict[str, Person],
    listing: Listing,
    telegram: FakeTelegramSession,
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    tenant, owner, other = people["tenant"], people["owner"], people["other"]
    tomorrow = viewing_days(datetime.now(UTC))[1]
    day = int(tomorrow.strftime("%Y%m%d"))
    telegram.calls.clear()

    await tenant.press(ChatCallback(action=ChatAction.VIEW, id=listing.id).pack())
    assert "Выберите день просмотра" in messages_to(telegram, TENANT_ID)[-1].text
    await tenant.press(ChatCallback(action=ChatAction.TIME, id=listing.id, day=day, hour=15).pack())

    request = messages_to(telegram, OWNER_ID)[-1]
    assert "ნახვის თხოვნა" in request.text
    assert f"{tomorrow:%d.%m}, 15:00" in request.text

    # Пока хозяин не подтвердил, другой арендатор может попросить то же время
    await other.press(ChatCallback(action=ChatAction.TIME, id=listing.id, day=day, hour=15).pack())
    second = messages_to(telegram, OWNER_ID)[-1]
    assert second is not request

    await owner.press(button_data(request, ChatAction.CONFIRM))
    confirmed = messages_to(telegram, TENANT_ID)[-1]
    assert "Хозяин подтвердил просмотр" in confirmed.text
    assert "ул. Чавчавадзе, 10" in confirmed.text

    # Второго на это же время подтвердить нельзя, а занятый час не предлагается
    await owner.press(button_data(second, ChatAction.CONFIRM))
    assert "დაკავებულია" in alerts(telegram)[-1]
    await other.press(ChatCallback(action=ChatAction.TIME, id=listing.id, day=day, hour=15).pack())
    assert "already taken" in alerts(telegram)[-1]
    await other.press(ChatCallback(action=ChatAction.DAY, id=listing.id, day=day).pack())
    hours = telegram.of(EditMessageText)[-1]
    assert "выберите время" not in hours.text, "на языке арендатора"
    texts = [b.text for row in hours.reply_markup.inline_keyboard for b in row]
    assert "14:00" in texts and "15:00" not in texts

    starts_at = viewing_start(tomorrow, 15)
    telegram.calls.clear()
    assert await send_viewing_reminders(bot, session_factory, starts_at - timedelta(hours=3)) == 0
    assert await send_viewing_reminders(bot, session_factory, starts_at - timedelta(hours=2)) == 1
    assert "Напоминание: просмотр сегодня в 15:00" in messages_to(telegram, TENANT_ID)[-1].text
    assert "შეხსენება" in messages_to(telegram, OWNER_ID)[-1].text
    assert await send_viewing_reminders(bot, session_factory, starts_at - timedelta(hours=1)) == 0

    async with session_factory() as session:
        statuses = sorted(
            v.status for v in (await session.execute(select(Viewing))).scalars().all()
        )
    assert statuses == ["confirmed", "pending"]


async def test_viewing_declined(
    people: dict[str, Person], listing: Listing, telegram: FakeTelegramSession
) -> None:
    tenant, owner = people["tenant"], people["owner"]
    day = int(viewing_days(datetime.now(UTC))[2].strftime("%Y%m%d"))
    await tenant.press(ChatCallback(action=ChatAction.TIME, id=listing.id, day=day, hour=11).pack())
    request = messages_to(telegram, OWNER_ID)[-1]
    await owner.press(button_data(request, ChatAction.DECLINE))
    declined = messages_to(telegram, TENANT_ID)[-1]
    assert "Хозяину не подходит" in declined.text
    button_data(declined, ChatAction.VIEW)
    await owner.press(button_data(request, ChatAction.CONFIRM))
    assert "უკვე უპასუხეთ" in alerts(telegram)[-1]


async def test_past_slot_rejected(
    people: dict[str, Person], listing: Listing, telegram: FakeTelegramSession
) -> None:
    yesterday = int((datetime.now(UTC) - timedelta(days=1)).strftime("%Y%m%d"))
    telegram.calls.clear()
    await people["tenant"].press(
        ChatCallback(action=ChatAction.TIME, id=listing.id, day=yesterday, hour=12).pack()
    )
    assert "уже недоступно" in alerts(telegram)[-1]
    assert not messages_to(telegram, OWNER_ID), "хозяину ничего не ушло"


async def test_new_chats_limit(
    people: dict[str, Person],
    listing: Listing,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from bina.application.chat import MAX_NEW_CHATS_PER_DAY, ChatError, ChatErrorCode
    from bina.application.use_cases.chat import ChatUseCase
    from bina.infrastructure.db.repositories.chat import ChatRepository

    now = datetime.now(UTC)
    async with session_factory() as session:
        tenant = (
            await session.execute(select(User).where(User.telegram_id == TENANT_ID))
        ).scalar_one()
        repository = ChatRepository(session)
        assert listing.owner_user_id is not None
        for _ in range(MAX_NEW_CHATS_PER_DAY):
            # Диалоги о других квартирах (созданы напрямую)
            other = await OwnerListingsRepository(session).create(
                listing.owner_user_id,
                OwnerListingDraft(
                    city="tbilisi",
                    district="Сабуртало",
                    rent_period="monthly",
                    price=Decimal(900),
                    currency="GEL",
                    rooms=1,
                    area=Decimal(40),
                    description="Уютная квартира рядом с метро Делиси.",
                    phone="+995555000000",
                ),
                f"limit-{_}",
                [],
                now,
            )
            await repository.create_conversation(other.id, tenant.id, listing.owner_user_id, now)
        use_case = ChatUseCase(repository)
        with pytest.raises(ChatError) as error:
            await use_case.start(listing.id, tenant, now)
        assert error.value.code == ChatErrorCode.LIMIT
        # Завтра — можно
        assert await use_case.start(listing.id, tenant, now + timedelta(days=1, minutes=1))
