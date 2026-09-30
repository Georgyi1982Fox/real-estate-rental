"""Напоминания об окончании Premium (TASK-107).

За ``REMIND_DAYS`` дня до окончания — «Premium закончится …, продлить: /premium»;
после окончания — «Premium закончился». Каждое сообщение — один раз на срок
окончания: после продления срок другой, и напоминания придут снова.
Сообщения — служебные уведомления: видны в Mini App и приходят в Telegram.
Не коммитит.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

REMIND_DAYS = 3
# Давно закончившимся не пишем (например, после первого запуска на старой базе)
EXPIRED_NOTICE_DAYS = 7

DATE_FORMAT = "%d.%m.%Y"

REMINDER: dict[str, str] = {
    "ka": "⏳ Premium მოქმედებს {date}-მდე. გააგრძელეთ: /premium — მყისიერი შეტყობინებები "
    "ახალ ბინებზე, ფასის ანალიზი, ხელშეკრულება და მიღების აქტი დარჩება თქვენთან.",
    "ru": "⏳ Premium действует до {date}. Продлить: /premium — мгновенные уведомления о "
    "новых квартирах, анализ цены, договор и акт приёмки останутся с вами.",
    "en": "⏳ Premium is active until {date}. Renew: /premium to keep instant alerts about "
    "new apartments, price analysis, the lease agreement and the handover report.",
}
EXPIRED: dict[str, str] = {
    "ka": "Premium დასრულდა. ახალ ბინებზე შეტყობინებები ახლა 3 საათის დაგვიანებით მოვა. "
    "გააგრძელეთ: /premium",
    "ru": "Premium закончился. Уведомления о новых квартирах теперь приходят с задержкой "
    "3 часа. Продлить: /premium",
    "en": "Premium has ended. Alerts about new apartments now arrive with a 3-hour delay. "
    "Renew: /premium",
}


@dataclass(frozen=True, slots=True)
class Subscriber:
    user_id: UUID
    expires_at: datetime


class IPremiumRemindersRepository(Protocol):
    async def expiring(self, now: datetime, until: datetime) -> list[Subscriber]:
        """Premium заканчивается в (now, until], напоминания на этот срок ещё не было."""
        ...

    async def expired(self, since: datetime, now: datetime) -> list[Subscriber]:
        """Premium закончился в (since, now], сообщения на этот срок ещё не было."""
        ...

    async def notify(self, user_id: UUID, texts: dict[str, str]) -> None: ...

    async def mark_reminded(self, subscriber: Subscriber) -> None: ...

    async def mark_expired_notified(self, subscriber: Subscriber) -> None: ...


@dataclass(frozen=True, slots=True)
class PremiumReminderStats:
    reminded: int
    expired: int


class PremiumRemindersUseCase:
    def __init__(self, repository: IPremiumRemindersRepository) -> None:
        self._repository = repository

    async def execute(self, now: datetime) -> PremiumReminderStats:
        expiring = await self._repository.expiring(now, now + timedelta(days=REMIND_DAYS))
        for subscriber in expiring:
            date = f"{subscriber.expires_at:{DATE_FORMAT}}"
            texts = {language: text.format(date=date) for language, text in REMINDER.items()}
            await self._repository.notify(subscriber.user_id, texts)
            await self._repository.mark_reminded(subscriber)
        expired = await self._repository.expired(now - timedelta(days=EXPIRED_NOTICE_DAYS), now)
        for subscriber in expired:
            await self._repository.notify(subscriber.user_id, dict(EXPIRED))
            await self._repository.mark_expired_notified(subscriber)
        return PremiumReminderStats(reminded=len(expiring), expired=len(expired))
