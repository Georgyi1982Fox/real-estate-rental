"""Свои данные в профиле бота: скачать и удалить (TASK-059, TASK-060), на PostgreSQL."""

import json

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import SendDocument, SendMessage
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, ReplyKeyboardRemove
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.bot.factory import create_dispatcher
from bina.infrastructure.bot.keyboards.callbacks import AccountAction, AccountCallback
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.db.models import User
from tests.support.people import Person
from tests.support.telegram import TOKEN, FakeTelegramSession

USER_ID = 6060


@pytest.fixture
def telegram() -> FakeTelegramSession:
    return FakeTelegramSession()


@pytest.fixture
def dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    return create_dispatcher(BotSettings(token=TOKEN), session_factory)


@pytest.fixture
async def person(dispatcher: Dispatcher, telegram: FakeTelegramSession) -> Person:
    person = Person(dispatcher, Bot(token=TOKEN, session=telegram), USER_ID, "ru")
    await person.send("/start")
    return person


def last_text(telegram: FakeTelegramSession) -> str:
    return telegram.of(SendMessage)[-1].text or ""


async def test_profile_export_and_delete(
    person: Person,
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await person.send("👤 Профиль")
    profile = telegram.of(SendMessage)[-1]
    assert isinstance(profile.reply_markup, InlineKeyboardMarkup)
    buttons = [b.text for row in profile.reply_markup.inline_keyboard for b in row]
    assert "📦 Скачать мои данные" in buttons and "🗑 Удалить аккаунт" in buttons

    await person.press(AccountCallback(action=AccountAction.EXPORT).pack())
    [sent] = telegram.of(SendDocument)
    assert isinstance(sent.document, BufferedInputFile)
    data = json.loads(sent.document.data)
    assert data["profile"]["telegram_id"] == USER_ID and data["service"] == "Bina.ai"

    await person.press(AccountCallback(action=AccountAction.ASK_DELETE).pack())
    assert "Удалить аккаунт и все данные?" in last_text(telegram)
    await person.press(AccountCallback(action=AccountAction.CANCEL).pack())
    async with session_factory() as session:
        alive = (await session.execute(select(User))).scalar_one()
        assert alive.telegram_id == USER_ID and not alive.is_deleted

    await person.press(AccountCallback(action=AccountAction.DELETE).pack())
    goodbye = telegram.of(SendMessage)[-1]
    assert "аккаунт и все данные удалены" in (goodbye.text or "")
    assert isinstance(goodbye.reply_markup, ReplyKeyboardRemove)
    async with session_factory() as session:
        gone = (await session.execute(select(User))).scalar_one()
        assert gone.is_deleted and gone.telegram_id < 0

    # Новый /start — чистый аккаунт
    await person.send("/start")
    async with session_factory() as session:
        users = (await session.execute(select(User).where(User.telegram_id == USER_ID))).all()
        assert len(users) == 1
