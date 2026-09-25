"""Бот целиком на настоящем PostgreSQL: реальные репозитории и транзакции."""

from datetime import UTC, datetime
from decimal import Decimal
from itertools import count

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerCallbackQuery, EditMessageReplyMarkup, EditMessageText
from aiogram.types import CallbackQuery, Chat, InlineKeyboardMarkup, Message, Update
from aiogram.types import User as TelegramUser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.use_cases.search_listings import SearchListingsUseCase
from bina.infrastructure.bot.factory import create_dispatcher
from bina.infrastructure.bot.keyboards.callbacks import (
    LanguageCallback,
    SearchCallback,
    SearchStep,
)
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.db.models import District, Listing
from tests.support.telegram import CHAT_ID, TOKEN, FakeTelegramSession

TG_USER = TelegramUser(id=CHAT_ID, is_bot=False, first_name="Nino", language_code="ru")
CHAT = Chat(id=CHAT_ID, type="private")


class Client:
    """Отправляет апдейты в Dispatcher от имени одного пользователя."""

    def __init__(self, dispatcher: Dispatcher, bot: Bot) -> None:
        self.dispatcher = dispatcher
        self.bot = bot
        self._ids = count(1)

    async def send(self, text_: str) -> None:
        message = Message(
            message_id=next(self._ids),
            date=datetime.now(UTC),
            chat=CHAT,
            from_user=TG_USER,
            text=text_,
        )
        await self.dispatcher.feed_update(
            self.bot, Update(update_id=next(self._ids), message=message)
        )

    async def press(self, data: str, markup: InlineKeyboardMarkup | None = None) -> None:
        message = Message(
            message_id=1, date=datetime.now(UTC), chat=CHAT, text="…", reply_markup=markup
        )
        query = CallbackQuery(
            id=str(next(self._ids)),
            from_user=TG_USER,
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
def client(
    session_factory: async_sessionmaker[AsyncSession],
    telegram: FakeTelegramSession,
) -> Client:
    dispatcher = create_dispatcher(BotSettings(token=TOKEN, page_size=2), session_factory)
    return Client(dispatcher, Bot(token=TOKEN, session=telegram))


@pytest.fixture
async def vake(session: AsyncSession) -> District:
    district = District(
        name_ru="Ваке", name_ka="ვაკე", name_en="Vake", avg_price_per_m2=Decimal(20),
        safety_score=9,
    )
    session.add(district)
    await session.flush()
    for n in range(3):
        session.add(
            Listing(
                source_id=f"mh-{n}", source_name="myhome", title_ru=f"Квартира {n}",
                title_ka="ბინა", description_ru="", description_ka="",
                price=Decimal(1000 + n * 100), district_id=district.id, rooms=2,
                area=Decimal(50),
            )
        )
    await session.commit()
    return district


async def scalar(session: AsyncSession, sql: str) -> object:
    return (await session.execute(text(sql))).scalar()


async def test_full_flow(
    client: Client,
    telegram: FakeTelegramSession,
    session: AsyncSession,
    vake: District,
) -> None:
    await client.send("/start")
    assert await scalar(session, "SELECT language FROM bina_users") == "ru"

    await client.press(SearchCallback(step=SearchStep.RESULTS, district=vake.id).pack())
    [results] = telegram.of(EditMessageText)
    assert "Найдено: <b>3</b>" in results.text
    assert results.reply_markup is not None

    first_star = results.reply_markup.inline_keyboard[0][0].callback_data
    assert first_star is not None
    await client.press(first_star, results.reply_markup)
    [flip] = telegram.of(EditMessageReplyMarkup)
    assert flip.reply_markup.inline_keyboard[0][0].text == "★ 1"
    assert await scalar(session, "SELECT count(*) FROM bina_favorites") == 1

    await client.press(LanguageCallback(code="en").pack())
    assert await scalar(session, "SELECT language FROM bina_users") == "en"


async def test_error_rolls_back_transaction(
    client: Client,
    telegram: FakeTelegramSession,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await client.send("/start")

    async def write_then_fail(self: SearchListingsUseCase, *args: object, **kwargs: object) -> None:
        await self.listings_repository._session.execute(  # type: ignore[attr-defined]
            text("UPDATE bina_users SET language = 'ka'")
        )
        raise RuntimeError("boom")

    monkeypatch.setattr(SearchListingsUseCase, "execute", write_then_fail)

    await client.press(SearchCallback(step=SearchStep.RESULTS).pack())

    assert await scalar(session, "SELECT language FROM bina_users") == "ru"
    [answer] = telegram.of(AnswerCallbackQuery)
    assert answer.show_alert is True
