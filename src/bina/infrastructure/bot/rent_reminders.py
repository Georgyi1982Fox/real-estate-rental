"""Отправка напоминания об оплате аренды с кнопкой «Оплачено» (TASK-109)."""

from datetime import date

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bina.application.rent_reminders import format_amount
from bina.application.use_cases.rent_reminders import DueReminder, SendResult
from bina.infrastructure.bot.handlers.rent import DATE_FORMAT, paid_keyboard
from bina.infrastructure.bot.texts import t

logger = structlog.get_logger(__name__)


def render_reminder(reminder: DueReminder, due: date, days: int) -> str:
    amount = format_amount(reminder.amount, reminder.currency)
    if days == 0:
        return t(reminder.language, "rent_due_today", amount=amount)
    return t(
        reminder.language,
        "rent_due_in",
        amount=amount,
        date=due.strftime(DATE_FORMAT),
        days=days,
    )


class TelegramRentReminderSender:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def __call__(self, reminder: DueReminder, due: date, days: int) -> str:
        try:
            await self._bot.send_message(
                reminder.telegram_id,
                render_reminder(reminder, due, days),
                reply_markup=paid_keyboard(reminder.language, reminder.id, due),
            )
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            # Бот заблокирован или чат недоступен: сегодня больше не пытаемся
            logger.info("Rent reminder not delivered", error=str(exc))
            return SendResult.BLOCKED
        except Exception as exc:  # noqa: BLE001 - сеть/Telegram: попробуем через час
            logger.warning("Rent reminder failed", error=str(exc))
            return SendResult.FAILED
        return SendResult.SENT
