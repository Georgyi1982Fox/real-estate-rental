"""Подпись договора двумя сторонами в боте (TASK-115), на настоящем PostgreSQL."""

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import SendDocument, SendMessage
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.signing import DocumentKind
from bina.application.use_cases.signing import SigningUseCase
from bina.infrastructure.bot.factory import create_dispatcher
from bina.infrastructure.bot.keyboards.callbacks import SignAction, SignCallback
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.db.models import SignedDocument, User
from bina.infrastructure.db.repositories.documents import DocumentsRepository
from tests.support.people import Person
from tests.support.telegram import TOKEN, FakeTelegramSession

LANDLORD, TENANT, STRANGER = 8101, 8102, 8103
PDF = b"%PDF-1.4 test contract"


@pytest.fixture
def telegram() -> FakeTelegramSession:
    return FakeTelegramSession()


@pytest.fixture
def dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    return create_dispatcher(BotSettings(token=TOKEN, rate_limit=100), session_factory)


@pytest.fixture
async def people(dispatcher: Dispatcher, telegram: FakeTelegramSession) -> dict[int, Person]:
    bot = Bot(token=TOKEN, session=telegram)
    people = {uid: Person(dispatcher, bot, uid, "ru") for uid in (LANDLORD, TENANT, STRANGER)}
    for person in people.values():
        await person.send("/start")
    return people


async def create(factory: async_sessionmaker[AsyncSession]) -> SignedDocument:
    async with factory() as session:
        creator = (
            await session.execute(select(User).where(User.telegram_id == LANDLORD))
        ).scalar_one()
        document = await SigningUseCase(DocumentsRepository(session)).create(
            creator, DocumentKind.CONTRACT, "Договор аренды: Нино — Гио", "contract.pdf", PDF, None
        )
        await session.commit()
        return document


def documents_to(telegram: FakeTelegramSession, chat_id: int) -> list[SendDocument]:
    return [call for call in telegram.of(SendDocument) if call.chat_id == chat_id]


def texts_to(telegram: FakeTelegramSession, chat_id: int) -> list[str]:
    return [call.text or "" for call in telegram.of(SendMessage) if call.chat_id == chat_id]


async def test_both_parties_sign_and_get_certificate(
    people: dict[int, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    document = await create(session_factory)
    telegram.calls.clear()

    # Создатель открывает ссылку: файл с кнопками и ссылка для второй стороны
    await people[LANDLORD].send(f"/start sign_{document.token}")
    [sent] = documents_to(telegram, LANDLORD)
    assert isinstance(sent.document, BufferedInputFile) and sent.document.data == PDF
    assert "ждёт подписей" in (sent.caption or "")
    assert isinstance(sent.reply_markup, InlineKeyboardMarkup)
    assert "Перешлите эту ссылку" in texts_to(telegram, LANDLORD)[-1]

    sign = SignCallback(action=SignAction.SIGN, id=document.id).pack()
    await people[LANDLORD].press(sign)
    await people[LANDLORD].press(sign)  # второй раз — «уже подписали», без ошибки

    await people[TENANT].send(f"/start sign_{document.token}")
    await people[TENANT].press(sign)
    assert "подписан обеими сторонами" in texts_to(telegram, LANDLORD)[-1]
    assert "подписан обеими сторонами" in texts_to(telegram, TENANT)[-1]
    certificates = [
        call.document
        for uid in (LANDLORD, TENANT)
        for call in documents_to(telegram, uid)
        if isinstance(call.document, BufferedInputFile)
        and (call.document.filename or "").startswith("certificate-")
    ]
    assert len(certificates) == 2 and certificates[0].data.startswith(b"%PDF")

    # Третий подписать не может
    await people[STRANGER].send(f"/start sign_{document.token}")
    assert documents_to(telegram, STRANGER)[-1].reply_markup is None

    async with session_factory() as session:
        stored = await session.get(SignedDocument, document.id)
        assert stored is not None and stored.status == "signed" and stored.completed_at
        signers = await DocumentsRepository(session).signers(document.id)
        assert {s.telegram_id for s in signers} == {LANDLORD, TENANT}


async def test_decline_and_my_documents(
    people: dict[int, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    document = await create(session_factory)
    await people[TENANT].send(f"/start sign_{document.token}")
    telegram.calls.clear()
    await people[TENANT].press(SignCallback(action=SignAction.DECLINE, id=document.id).pack())
    assert "отказался(ась)" in texts_to(telegram, LANDLORD)[-1]

    await people[LANDLORD].press(SignCallback(action=SignAction.LIST).pack())
    listing = telegram.of(SendMessage)[-1]
    assert "Мои документы" in (listing.text or "")
    assert isinstance(listing.reply_markup, InlineKeyboardMarkup)
    assert listing.reply_markup.inline_keyboard[0][0].text.startswith("❌ Договор аренды")

    await people[STRANGER].send("/start sign_unknown-token-123")
    assert "Документ не найден" in texts_to(telegram, STRANGER)[-1]
    # Чужой документ по кнопке не открыть
    await people[STRANGER].press(SignCallback(action=SignAction.OPEN, id=document.id).pack())
    assert not documents_to(telegram, STRANGER)
