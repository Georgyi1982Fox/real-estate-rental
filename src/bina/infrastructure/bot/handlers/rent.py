"""``/rent``: напоминания об оплате аренды (TASK-109).

Список напоминаний → «Добавить» → день месяца (кнопки 1-28) → сумма сообщением.
Состояние «жду сумму» хранится в памяти бота (FSM): после перезапуска бота
пользователь просто начнёт заново.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.rent_reminders import (
    MAX_DAY,
    MAX_REMINDERS,
    format_amount,
    parse_amount,
)
from bina.infrastructure.bot.keyboards.callbacks import RentAction, RentCallback
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import RentReminder, User
from bina.infrastructure.db.repositories.rent_reminders import RentRemindersRepository

DATE_FORMAT = "%d.%m.%Y"
DAYS_PER_ROW = 7


class RentStates(StatesGroup):
    amount = State()


def render_list(language: str, reminders: list[RentReminder]) -> str:
    lines = []
    for reminder in reminders:
        amount = format_amount(reminder.amount, reminder.currency)
        if reminder.paid_for is not None:
            lines.append(
                t(
                    language,
                    "rent_item_paid",
                    day=reminder.day,
                    amount=amount,
                    date=reminder.paid_for.strftime(DATE_FORMAT),
                )
            )
        else:
            lines.append(t(language, "rent_item", day=reminder.day, amount=amount))
    items = "\n".join(lines) if lines else t(language, "rent_empty")
    return t(language, "rent_info", items=items)


def list_keyboard(language: str, reminders: list[RentReminder]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for reminder in reminders:
        builder.button(
            text=t(language, "rent_delete", day=reminder.day),
            callback_data=RentCallback(action=RentAction.DELETE, reminder=reminder.id),
        )
    if len(reminders) < MAX_REMINDERS:
        builder.button(
            text=t(language, "rent_add"), callback_data=RentCallback(action=RentAction.ADD)
        )
    builder.adjust(1)
    return with_home(builder.as_markup(), language)


def days_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for day in range(1, MAX_DAY + 1):
        builder.button(text=str(day), callback_data=RentCallback(action=RentAction.DAY, day=day))
    builder.adjust(DAYS_PER_ROW)
    return builder.as_markup()


def paid_keyboard(language: str, reminder_id: UUID, due: date) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t(language, "rent_paid_button"),
        callback_data=RentCallback(
            action=RentAction.PAID, reminder=reminder_id, due=due.strftime("%Y%m%d")
        ),
    )
    return builder.as_markup()


async def cmd_rent(message: Message, user: User, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    reminders = await RentRemindersRepository(session).list_for_user(user.id)
    await message.answer(
        render_list(user.language, reminders), reply_markup=list_keyboard(user.language, reminders)
    )


async def on_add(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    if await RentRemindersRepository(session).count_for_user(user.id) >= MAX_REMINDERS:
        await callback.answer(t(user.language, "rent_limit", limit=MAX_REMINDERS), show_alert=True)
        return
    if callback.message is not None:
        await callback.message.answer(
            t(user.language, "rent_choose_day"), reply_markup=days_keyboard()
        )
    await callback.answer()


async def on_day(
    callback: CallbackQuery, callback_data: RentCallback, user: User, state: FSMContext
) -> None:
    await state.set_state(RentStates.amount)
    await state.update_data(day=callback_data.day)
    if callback.message is not None:
        await callback.message.answer(t(user.language, "rent_enter_amount", day=callback_data.day))
    await callback.answer()


async def on_amount(message: Message, user: User, session: AsyncSession, state: FSMContext) -> None:
    parsed = parse_amount(message.text or "")
    if parsed is None:
        await message.answer(t(user.language, "rent_bad_amount"))
        return
    day = int((await state.get_data())["day"])
    await state.clear()
    repository = RentRemindersRepository(session)
    if await repository.count_for_user(user.id) >= MAX_REMINDERS:
        await message.answer(t(user.language, "rent_limit", limit=MAX_REMINDERS))
        return
    amount, currency = parsed
    await repository.add(user.id, day, amount, currency)
    await message.answer(
        t(user.language, "rent_saved", amount=format_amount(amount, currency), day=day)
    )


async def on_delete(
    callback: CallbackQuery, callback_data: RentCallback, user: User, session: AsyncSession
) -> None:
    repository = RentRemindersRepository(session)
    if callback_data.reminder is not None:
        await repository.delete(user.id, callback_data.reminder)
    await callback.answer(t(user.language, "rent_deleted"))
    if callback.message is not None:
        reminders = await repository.list_for_user(user.id)
        await callback.message.answer(
            render_list(user.language, reminders),
            reply_markup=list_keyboard(user.language, reminders),
        )


async def on_paid(
    callback: CallbackQuery, callback_data: RentCallback, user: User, session: AsyncSession
) -> None:
    if callback_data.reminder is None or callback_data.due is None:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    due = datetime.strptime(callback_data.due, "%Y%m%d").replace(tzinfo=UTC).date()
    marked = await RentRemindersRepository(session).mark_paid(user.id, callback_data.reminder, due)
    if not marked:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(
            t(user.language, "rent_paid_done", date=due.strftime(DATE_FORMAT))
        )


def create_router() -> Router:
    router = Router(name="rent")
    router.message.register(cmd_rent, Command("rent"))
    router.message.register(on_amount, StateFilter(RentStates.amount), F.text)
    router.callback_query.register(on_add, RentCallback.filter(F.action == RentAction.ADD))
    router.callback_query.register(on_day, RentCallback.filter(F.action == RentAction.DAY))
    router.callback_query.register(on_delete, RentCallback.filter(F.action == RentAction.DELETE))
    router.callback_query.register(on_paid, RentCallback.filter(F.action == RentAction.PAID))
    return router
