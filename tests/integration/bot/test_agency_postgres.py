"""Кабинет риелтора / агентства в боте (TASK-100), на настоящем PostgreSQL."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerPreCheckoutQuery, SendInvoice, SendMessage
from aiogram.types import Contact, InlineKeyboardMarkup, SuccessfulPayment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.agencies import bump_hour
from bina.application.owner_listings import OwnerListingDraft
from bina.application.use_cases.agencies import run_bumps
from bina.infrastructure.bot.factory import create_dispatcher
from bina.infrastructure.bot.keyboards.callbacks import AgencyAction, AgencyCallback
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.db.models import Agency, Listing, User
from bina.infrastructure.db.repositories.agencies import (
    AgenciesRepository,
    ListingStatsRepository,
)
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository
from tests.support.people import Person
from tests.support.telegram import TOKEN, FakeTelegramSession

REALTOR_ID = 4004
ADMIN_ID = 555


@pytest.fixture(autouse=True)
def paid_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PREMIUM_FOR_ALL", raising=False)
    monkeypatch.delenv("AGENCY_PLANS", raising=False)
    monkeypatch.delenv("AGENCY_FREE_LISTINGS", raising=False)
    monkeypatch.delenv("BUMP_PRICE_STARS", raising=False)


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
        "realtor": Person(dispatcher, bot, REALTOR_ID, "ru"),
        "admin": Person(dispatcher, bot, ADMIN_ID, "ru"),
    }
    for person in people.values():
        await person.send("/start")
    return people


def texts_to(telegram: FakeTelegramSession, chat_id: int) -> list[str]:
    return [call.text or "" for call in telegram.of(SendMessage) if call.chat_id == chat_id]


async def register(realtor: Person) -> None:
    await realtor.press(AgencyCallback(action=AgencyAction.JOIN).pack())
    await realtor.send("В")  # слишком коротко — переспросит
    await realtor.send("Ваке Риелти")
    await realtor.message(
        contact=Contact(phone_number="+995 555 11 22 33", first_name="R", user_id=REALTOR_ID)
    )


def draft(n: int) -> OwnerListingDraft:
    return OwnerListingDraft(
        city="tbilisi",
        district="Ваке",
        rent_period="monthly",
        price=Decimal(1000 + n),
        currency="GEL",
        rooms=2,
        area=Decimal(60),
        description="Квартира агентства с ремонтом рядом с парком Ваке.",
        phone="+995555112233",
        agency_name="Ваке Риелти",
    )


async def add_listings(
    session_factory: async_sessionmaker[AsyncSession], count: int
) -> list[Listing]:
    async with session_factory() as session:
        user = (
            await session.execute(select(User).where(User.telegram_id == REALTOR_ID))
        ).scalar_one()
        repository = OwnerListingsRepository(session)
        listings = [
            await repository.create(user.id, draft(n), f"ag-{n}", [], datetime.now(UTC))
            for n in range(count)
        ]
        await session.commit()
        return listings


async def test_register_and_cabinet_with_stats(
    people: dict[str, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    realtor = people["realtor"]
    telegram.calls.clear()
    await register(realtor)

    sent = texts_to(telegram, REALTOR_ID)
    assert any("Напишите название агентства" in text for text in sent)
    assert any("от 2 до 80" in text for text in sent)
    assert any(
        "Кабинет «Ваке Риелти» готов" in text and "до 10 объявлений" in text for text in sent
    )
    admin_alert = texts_to(telegram, ADMIN_ID)[-1]
    assert "Новый риелтор" in admin_alert and "+995555112233" in admin_alert

    [listing] = await add_listings(session_factory, 1)
    async with session_factory() as session:
        stats = ListingStatsRepository(session)
        today = datetime.now(UTC).date()
        await stats.record(listing, today, view=True)
        await stats.record(listing, today, view=True)
        await stats.record(listing, today)
        await session.commit()

    await realtor.press(AgencyCallback(action=AgencyAction.CABINET).pack())
    cabinet = texts_to(telegram, REALTOR_ID)[-1]
    assert "Ваке Риелти" in cabinet and "Пакет: бесплатный" in cabinet
    assert "В поиске: 1 из 10" in cabinet
    assert "👁 2 · 💬 1 · ✉️ 0 · 📅 0 · ❤️ 0" in cabinet

    async with session_factory() as session:
        stored = await session.get(Listing, listing.id)
        assert stored is not None
        assert (stored.owner_type, stored.owner_name) == ("agent", "Ваке Риелти")


async def test_agency_buys_plan_and_premium_listing(
    people: dict[str, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    realtor = people["realtor"]
    await register(realtor)
    [listing] = await add_listings(session_factory, 1)
    telegram.calls.clear()

    await realtor.press(AgencyCallback(action=AgencyAction.PLANS).pack())
    assert "20 объявлений — 300 ⭐" in texts_to(telegram, REALTOR_ID)[-1]
    await realtor.press(AgencyCallback(action=AgencyAction.BUY, value="start").pack())
    [invoice] = telegram.of(SendInvoice)
    assert (invoice.payload, [p.amount for p in invoice.prices]) == ("agency:start", [300])
    await realtor.pre_checkout("agency:start", 299)
    await realtor.pre_checkout("agency:start", 300)
    assert [a.ok for a in telegram.of(AnswerPreCheckoutQuery)] == [False, True]
    await realtor.message(
        successful_payment=SuccessfulPayment(
            currency="XTR",
            total_amount=300,
            invoice_payload="agency:start",
            telegram_payment_charge_id="plan-1",
            provider_payment_charge_id="",
        )
    )
    assert "Пакет оплачен:</b> 20 объявлений" in texts_to(telegram, REALTOR_ID)[-1]

    await realtor.press(AgencyCallback(action=AgencyAction.BUMP, listing=listing.id).pack())
    bump_invoice = telegram.of(SendInvoice)[-1]
    assert bump_invoice.payload == f"bump:{listing.id}"
    assert [p.amount for p in bump_invoice.prices] == [100]
    await realtor.message(
        successful_payment=SuccessfulPayment(
            currency="XTR",
            total_amount=100,
            invoice_payload=f"bump:{listing.id}",
            telegram_payment_charge_id="bump-1",
            provider_payment_charge_id="",
        )
    )
    assert "Premium до" in texts_to(telegram, REALTOR_ID)[-1]

    await realtor.press(AgencyCallback(action=AgencyAction.CABINET).pack())
    cabinet = texts_to(telegram, REALTOR_ID)[-1]
    assert "Пакет: 20 объявлений" in cabinet and "1 из 20" in cabinet
    assert "⭐ до" in cabinet

    async with session_factory() as session:
        agency = (await session.execute(select(Agency))).scalar_one()
        assert agency.plan == "start"
        stored = await session.get(Listing, listing.id)
        assert stored is not None and stored.bump_until is not None


async def test_testing_mode_is_free(
    people: dict[str, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PREMIUM_FOR_ALL", "1")
    realtor = people["realtor"]
    await register(realtor)
    [listing] = await add_listings(session_factory, 1)
    await realtor.press(AgencyCallback(action=AgencyAction.BUMP, listing=listing.id).pack())
    assert not telegram.of(SendInvoice)
    assert "Premium до" in texts_to(telegram, REALTOR_ID)[-1]
    await realtor.press(AgencyCallback(action=AgencyAction.CABINET).pack())
    cabinet = texts_to(telegram, REALTOR_ID)[-1]
    assert "тестовый режим" in cabinet and "1 из 40" in cabinet


async def test_daily_bumps_are_spread(
    people: dict[str, Person], session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await register(people["realtor"])
    listings = await add_listings(session_factory, 5)
    # Позже всех — в 21:00 по Тбилиси (17:00 UTC): к этому времени час наступил у всех
    late = datetime.now(UTC).replace(hour=17, minute=30) + timedelta(days=1)
    async with session_factory() as session:
        for listing in listings:
            stored = await session.get(Listing, listing.id)
            assert stored is not None
            stored.bump_until = late + timedelta(days=10)
        await session.commit()
        repository = AgenciesRepository(session)
        assert await run_bumps(repository, late) == 3, "не больше 3 за раз у одного агентства"
        await session.commit()
        assert await run_bumps(repository, late + timedelta(hours=1)) == 2
        await session.commit()
        assert await run_bumps(repository, late + timedelta(hours=2)) == 0, "раз в сутки"
        bumped = [await session.get(Listing, item.id) for item in listings]
        assert all(item is not None and item.bumped_at is not None for item in bumped)
    assert all(9 <= bump_hour(item.id) <= 21 for item in listings)


async def test_admin_blocks_agency(
    people: dict[str, Person],
    telegram: FakeTelegramSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    realtor, admin = people["realtor"], people["admin"]
    await register(realtor)
    listings = await add_listings(session_factory, 2)
    alert = [c for c in telegram.of(SendMessage) if c.chat_id == ADMIN_ID][-1]
    assert isinstance(alert.reply_markup, InlineKeyboardMarkup)
    block = alert.reply_markup.inline_keyboard[0][0].callback_data or ""

    await realtor.press(block)  # не админ — ничего
    await admin.press(block)
    assert "скрыто объявлений: 2" in texts_to(telegram, ADMIN_ID)[-1]

    async with session_factory() as session:
        hidden = [await session.get(Listing, item.id) for item in listings]
        assert all(item is not None and item.hidden_at is not None for item in hidden)
    await realtor.press(AgencyCallback(action=AgencyAction.CABINET).pack())
    assert "заблокирован" in texts_to(telegram, REALTOR_ID)[-1]
