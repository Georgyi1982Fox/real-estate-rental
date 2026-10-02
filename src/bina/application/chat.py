"""Чат с хозяином через бота с AI-переводом и запись на просмотр (TASK-111, TASK-112).

Работает для объявлений, которые хозяева разместили сами (TASK-096): у них есть
хозяин в системе. Арендатор пишет в боте на своём языке, бот переводит на язык
хозяина и пересылает (и обратно). Телеграм-имена и ID друг другу не показываются.

Просмотр: арендатор выбирает день (ближайшие ``VIEWING_DAYS``) и час
(``FIRST_HOUR``…``LAST_HOUR`` по Тбилиси), хозяин подтверждает или отказывает.
За ``REMIND_BEFORE`` до подтверждённого просмотра бот напоминает обоим.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from uuid import UUID

from bina.application.rent_reminders import TBILISI

# Новых диалогов в сутки у одного арендатора (защита хозяев от спама)
MAX_NEW_CHATS_PER_DAY = 5
MAX_MESSAGE_LENGTH = 2000
# Неотвеченных просьб о просмотре у арендатора одновременно
MAX_PENDING_VIEWINGS = 3
VIEWING_DAYS = 7
FIRST_HOUR = 10
LAST_HOUR = 20
REMIND_BEFORE = timedelta(hours=2)
# Просмотр длится час: другой просмотр той же квартиры в этот час не записать
VIEWING_LENGTH = timedelta(hours=1)
# Ссылка ``t.me/<бот>?start=chat_<id объявления>`` (кнопка сайта)
START_PREFIX = "chat_"


class ViewingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"


class ChatErrorCode(StrEnum):
    NOT_FOUND = "not_found"  # объявления нет, оно не от хозяина или снято
    OWN_LISTING = "own_listing"  # своё объявление
    LIMIT = "limit"  # слишком много новых диалогов за сутки
    TOO_LONG = "too_long"
    EMPTY = "empty"
    SLOT_TAKEN = "slot_taken"
    SLOT_INVALID = "slot_invalid"  # прошло или вне рабочих часов
    TOO_MANY_VIEWINGS = "too_many_viewings"
    ALREADY_ANSWERED = "already_answered"


class ChatError(Exception):
    """Сообщение или просмотр нельзя отправить (код — для текста пользователю)."""

    def __init__(self, code: ChatErrorCode) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class Participant:
    """Кому доставить сообщение: Telegram-чат и язык."""

    telegram_id: int
    language: str


def local_today(now: datetime) -> date:
    return now.astimezone(TBILISI).date()


def viewing_days(now: datetime) -> list[date]:
    """Дни, на которые можно записаться: сегодня (если ещё есть часы) и дальше."""
    today = local_today(now)
    days = [today + timedelta(days=offset) for offset in range(VIEWING_DAYS)]
    return [day for day in days if viewing_hours(day, now)]


def viewing_hours(day: date, now: datetime) -> list[int]:
    """Свободные по времени часы дня (не раньше чем через час от ``now``)."""
    earliest = now + VIEWING_LENGTH
    return [
        hour for hour in range(FIRST_HOUR, LAST_HOUR + 1) if viewing_start(day, hour) >= earliest
    ]


def viewing_start(day: date, hour: int) -> datetime:
    """Начало просмотра по Тбилиси (с часовым поясом)."""
    return datetime.combine(day, time(hour), tzinfo=TBILISI)


def valid_slot(starts_at: datetime, now: datetime) -> bool:
    local = starts_at.astimezone(TBILISI)
    return (
        local.minute == 0
        and local.date() in viewing_days(now)
        and local.hour in viewing_hours(local.date(), now)
    )


def chat_link(bot_username: str, listing_id: UUID | str) -> str:
    """Ссылка «написать хозяину через бота» — кнопка «Написать» у объявлений хозяев."""
    return f"https://t.me/{bot_username}?start={START_PREFIX}{listing_id}"


def listing_from_start(payload: str | None) -> str | None:
    """ID объявления из ``/start chat_<id>``; ``None`` — это не ссылка на чат."""
    if not payload or not payload.startswith(START_PREFIX):
        return None
    return payload.removeprefix(START_PREFIX).strip() or None


def clean_message(text: str | None) -> str:
    """Текст сообщения; пустой или слишком длинный — :class:`ChatError`."""
    message = (text or "").strip()
    if not message:
        raise ChatError(ChatErrorCode.EMPTY)
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ChatError(ChatErrorCode.TOO_LONG)
    return message
