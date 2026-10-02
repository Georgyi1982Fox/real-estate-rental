"""«🔥 Топ» за звёзды и «✅ Проверенный собственник» (TASK-097, TASK-098), на PostgreSQL."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import (
    AnswerCallbackQuery,
    AnswerPreCheckoutQuery,
    DeleteMessage,
    SendInvoice,
    SendMessage,
    SendPhoto,
)
from aiogram.types import InlineKeyboardMarkup, PhotoSize, SuccessfulPayment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.owner_listings import OwnerListingDraft
from bina.application.promotion import promotion_payload
from bina.infrastructure.bot.factory import create_dispatcher
from bina.infrastructure.bot.keyboards.callbacks import (
    AdminCallback,
    OwnerAction,
    OwnerCallback,
)
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.db.models import Listing, Payment, User, Verification
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository
from tests.support.people import Person
from tests.support.telegram import TOKEN, FakeTelegramSession

OWNER_ID = 2002
ADMIN_ID = 555


@pytest.fixture
def telegram() -> FakeTelegramSession:
    return FakeTelegramSession()


@pytest.fixture
def dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    return create_dispatcher(BotSettings(token=TOKEN, admin_ids=(ADMIN_ID,)), session_factory)


@pytest.fixture
async def people(dispatcher: Dispatcher, telegram: FakeTelegramSession) -> dict[str, Person]:
    bot = Bot(token=TOKEN, session=telegram)
    people = {
        "owner": Person(dispatcher, bot, OWNER_ID, "ru"),
        "admin": Person(dispatcher, bot, ADMIN_ID, "ru"),
    }
    for person in people.values():
        await person.send("/start")
    return people


def draft(district: str = "Ваке") -> OwnerListingDraft:
    return OwnerListingDraft(
        city="tbilisi",
        district=district,
        rent_period="monthly",
        price=Decimal(1500),
        currency="GEL",
        rooms=2,
        area=Decimal(60),
        description="Светлая квартира с новым ремонтом, рядом парк Ваке.",
        phone="+995555123456",
    )


@pytest.fixture
async def listing(
    people: dict[str, Person], session_factory: async_sessionmaker[AsyncSession]
) -> Listing:
    async with session_factory() as session:
        owner = (
            await session.execute(select(User).where(User.telegram_id == OWNER_ID))
        ).scalar_one()
        created = await OwnerListingsRepository(session).create(
            owner.id, draft(), "promo-test", [], datetime.now(UTC) - timedelta(days=3)
        )
        created.created_at = datetime.now(UTC) - timedelta(days=3)
        await session.commit()
        return created


def texts_to(telegram: FakeTelegramSession, chat_id: int) -> list[str]:
    return [call.text or "" for call in telegram.of(SendMessage) if call.chat_id == chat_id]


def alerts(telegram: FakeTelegramSession) -> list[str]:
    return [call.text or "" for call in telegram.of(AnswerCallbackQuery)]


async def pay(owner: Person, payload: str, charge_id: str, amount: int = 150) -> None:
    await owner.message(
        successful_payment=SuccessfulPayment(
            currency="XTR",
            total_amount=amount,
            invoice_payload=payload,
            telegram_payment_charge_id=charge_id,
            provider_payment_charge_id="",
        )
    )


async def test_promotion_paid_with_stars(
    people: dict[str, Person],
    listing: Listing,
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = people["owner"]
    telegram.calls.clear()

    await owner.send("/mylistings")
    my_list = telegram.of(SendMessage)[-1]
    assert isinstance(my_list.reply_markup, InlineKeyboardMarkup)
    buttons = [b.text for row in my_list.reply_markup.inline_keyboard for b in row]
    assert "🔥 Топ" in buttons and "✅ Проверка" in buttons, "одно объявление — без номера"

    await owner.press(OwnerCallback(action=OwnerAction.PROMOTE, listing=listing.id).pack())
    [invoice] = telegram.of(SendInvoice)
    assert invoice.payload == promotion_payload(listing.id)
    assert invoice.currency == "XTR"
    assert [price.amount for price in invoice.prices] == [150]
    assert "Топ на 7 дней" in invoice.title

    await owner.pre_checkout(invoice.payload, 100)  # не та сумма
    await owner.pre_checkout(invoice.payload, 150)
    assert [answer.ok for answer in telegram.of(AnswerPreCheckoutQuery)] == [False, True]

    await pay(owner, invoice.payload, "charge-1")
    assert "Объявление в топе до" in texts_to(telegram, OWNER_ID)[-1]
    await pay(owner, invoice.payload, "charge-1")  # Telegram прислал повторно

    async with session_factory() as session:
        stored = await session.get(Listing, listing.id)
        assert stored is not None and stored.promoted_until is not None
        days = (stored.promoted_until - datetime.now(UTC)).total_seconds() / 86400
        assert 6.9 < days <= 7, "повтор не продлевает"
        payments = (await session.execute(select(Payment))).scalars().all()
        assert [(p.plan, int(p.amount)) for p in payments] == [("promo", 150)]

        # Наверху поиска, хотя есть объявление новее
        owner_user = await session.get(User, stored.owner_user_id)
        assert owner_user is not None
        newer = await OwnerListingsRepository(session).create(
            owner_user.id, draft("Сабуртало"), "newer", [], datetime.now(UTC)
        )
        await session.commit()
        found = await ListingsRepository(session).search(ListingSearchFilters(), limit=10)
        assert [item.id for item in found] == [listing.id, newer.id]
        assert found[0].promoted_until is not None

        # И снова в уведомлениях — первым, хотя создано давно
        since = datetime.now(UTC) - timedelta(hours=1)
        fresh = await ListingsRepository(session).search_created_since(
            ListingSearchFilters(), since, limit=10
        )
        assert [item.id for item in fresh] == [listing.id, newer.id]

    telegram.calls.clear()
    await owner.send("/mylistings")
    assert "🔥 в топе до" in texts_to(telegram, OWNER_ID)[-1]


async def test_cannot_promote_taken_down_listing(
    people: dict[str, Person], listing: Listing, telegram: FakeTelegramSession
) -> None:
    owner = people["owner"]
    await owner.press(OwnerCallback(action=OwnerAction.OFF, listing=listing.id).pack())
    await owner.press(OwnerCallback(action=OwnerAction.PROMOTE, listing=listing.id).pack())
    assert "Сначала верните объявление в поиск" in alerts(telegram)[-1]
    assert not telegram.of(SendInvoice)
    await owner.pre_checkout(promotion_payload(listing.id), 150)
    assert telegram.of(AnswerPreCheckoutQuery)[-1].ok is False


async def send_document(owner: Person, listing: Listing) -> None:
    await owner.press(OwnerCallback(action=OwnerAction.VERIFY, listing=listing.id).pack())
    await owner.send("вот документ")  # текст — попросит фото или файл
    size = PhotoSize(file_id="doc-file", file_unique_id="doc", width=1200, height=1600)
    await owner.message(photo=[size])


async def test_owner_verified_by_admin(
    people: dict[str, Person],
    listing: Listing,
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner, admin = people["owner"], people["admin"]
    telegram.calls.clear()
    await send_document(owner, listing)

    sent = texts_to(telegram, OWNER_ID)
    assert any("выписки из Публичного реестра" in text for text in sent)
    assert any("Пришлите документ фотографией или файлом" in text for text in sent)
    assert "отправлен на проверку" in sent[-1]

    [to_admin] = telegram.of(SendPhoto)
    assert (to_admin.chat_id, to_admin.photo) == (ADMIN_ID, "doc-file")
    assert "Проверка собственника" in (to_admin.caption or "")

    # Второй раз, пока документ проверяется, — нельзя
    await owner.press(OwnerCallback(action=OwnerAction.VERIFY, listing=listing.id).pack())
    assert "уже на проверке" in alerts(telegram)[-1]
    await owner.send("/mylistings")
    assert "⏳ документ на проверке" in texts_to(telegram, OWNER_ID)[-1]

    assert isinstance(to_admin.reply_markup, InlineKeyboardMarkup)
    approve = to_admin.reply_markup.inline_keyboard[0][0].callback_data or ""
    await admin.press(approve)
    assert telegram.of(DeleteMessage), "документ удалён из чата администратора"
    assert "Собственник подтверждён" in texts_to(telegram, ADMIN_ID)[-1]
    assert "Проверенный собственник" in texts_to(telegram, OWNER_ID)[-1]

    await admin.press(approve)  # повторное нажатие
    assert "устарело" in alerts(telegram)[-1]

    async with session_factory() as session:
        stored = await session.get(Listing, listing.id)
        assert stored is not None and stored.is_verified
        [verification] = (await session.execute(select(Verification))).scalars().all()
        assert (verification.status, verification.file_id) == ("approved", None)

    await owner.send("/mylistings")
    assert "✅ проверено" in texts_to(telegram, OWNER_ID)[-1]


async def test_verification_rejected_and_only_admin_decides(
    people: dict[str, Person],
    listing: Listing,
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner, admin = people["owner"], people["admin"]
    await send_document(owner, listing)
    [to_admin] = telegram.of(SendPhoto)
    assert isinstance(to_admin.reply_markup, InlineKeyboardMarkup)
    approve, reject = (b.callback_data or "" for b in to_admin.reply_markup.inline_keyboard[0])
    assert AdminCallback.unpack(reject).request is not None

    await owner.press(approve)  # не админ — ничего не происходит
    await admin.press(reject)
    assert "Не удалось подтвердить" in texts_to(telegram, OWNER_ID)[-1]

    async with session_factory() as session:
        stored = await session.get(Listing, listing.id)
        assert stored is not None and not stored.is_verified
        [verification] = (await session.execute(select(Verification))).scalars().all()
        assert verification.status == "rejected"
