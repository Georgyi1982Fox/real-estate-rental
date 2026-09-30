"""Уведомления в Telegram: текст, кнопка, ошибки доставки (TASK-028)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.methods import SendMessage

from bina.application.ports.notification_sender import DeliveryResult, INotificationSender
from bina.application.repositories.notifications import PendingNotification
from bina.application.use_cases.notifications import DeliverNotificationsUseCase
from bina.infrastructure.bot.notifications import TelegramNotificationSender, render_notification
from bina.infrastructure.db.models import Listing, Notification

METHOD = SendMessage(chat_id=1, text="x")
NOW = datetime(2026, 9, 28, 12, tzinfo=UTC)


def listing(**overrides: Any) -> Listing:
    values: dict[str, Any] = {
        "id": uuid4(),
        "title_ru": "Квартира в <Ваке>",
        "title_ka": "",
        "title_en": "Flat in Vake",
        "price": Decimal(1500),
        "currency": "GEL",
        "rooms": 2,
        "area": Decimal("60.5"),
        "url": "https://home.ss.ge/ru/1",
        "is_deleted": False,
    }
    values.update(overrides)
    return cast(Listing, SimpleNamespace(**values))


def pending(
    kind: str = "new_listing",
    language: str = "ru",
    item: Listing | None = None,
    search_name: str | None = "Ваке, 2 комн.",
    created_at: datetime = NOW,
    **fields: Any,
) -> PendingNotification:
    notification = cast(
        Notification,
        SimpleNamespace(
            id=uuid4(),
            type=kind,
            old_price=fields.get("old_price"),
            new_price=fields.get("new_price"),
            text=fields.get("text"),
            created_at=created_at,
        ),
    )
    return PendingNotification(
        notification=notification,
        telegram_id=555,
        language=language,
        listing=item if item is not None else listing(),
        search_name=search_name,
    )


def test_new_listing_text_and_mini_app_button() -> None:
    item = listing()
    rendered = render_notification(pending(item=item), "https://bina.example.com/")
    assert rendered is not None
    text, keyboard = rendered
    assert text.startswith("🏠 <b>Новая квартира</b> по поиску «Ваке, 2 комн.»")
    assert "<b>Квартира в &lt;Ваке&gt;</b>" in text  # HTML экранирован
    assert "1 500 ₾ · 2 комн. · 60.5 м²" in text
    assert keyboard is not None
    button = keyboard.inline_keyboard[0][0]
    assert button.text == "Открыть"
    assert button.web_app is not None
    assert button.web_app.url == f"https://bina.example.com/listing/{item.id}"


def test_price_drop_in_english_with_source_link() -> None:
    rendered = render_notification(
        pending("price_drop", "en", old_price=Decimal(1800), new_price=Decimal(1500)), None
    )
    assert rendered is not None
    text, keyboard = rendered
    assert text.startswith("📉 <b>Price dropped</b>: 1 800 ₾ → <b>1 500 ₾</b>")
    assert "<b>Flat in Vake</b>" in text
    assert keyboard is not None
    assert keyboard.inline_keyboard[0][0].url == "https://home.ss.ge/ru/1"


def test_georgian_user_gets_georgian_interface() -> None:
    rendered = render_notification(pending(language="ka", search_name=None), None)
    assert rendered is not None
    assert rendered[0].startswith("🏠 <b>ახალი ბინა</b> თქვენი ძებნით")


def test_nothing_to_send() -> None:
    assert render_notification(pending(item=listing(is_deleted=True)), None) is None
    assert render_notification(pending("system", text=None), None) is None
    system = render_notification(pending("system", "ka", text={"en": "Hello <3"}), None)
    assert system == ("Hello &lt;3", None)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (None, DeliveryResult.SENT),
        (
            TelegramForbiddenError(METHOD, "bot was blocked by the user"),
            DeliveryResult.UNDELIVERABLE,
        ),
        (TelegramNetworkError(METHOD, "timeout"), DeliveryResult.RETRY),
        (TelegramRetryAfter(METHOD, "flood", retry_after=0), DeliveryResult.RETRY),
    ],
)
async def test_sender_results(error: Exception | None, expected: DeliveryResult) -> None:
    bot = AsyncMock()
    bot.send_message.side_effect = error
    sender = TelegramNotificationSender(bot, "https://bina.example.com", send_interval=0)

    assert await sender.send(pending()) is expected
    kwargs = bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == 555
    assert kwargs["disable_web_page_preview"] is True


class ScriptedSender(INotificationSender):
    def __init__(self, results: list[DeliveryResult]) -> None:
        self.results = results

    async def send(self, pending: PendingNotification) -> DeliveryResult:
        return self.results.pop(0)


async def test_delivery_marks_done_and_keeps_retries() -> None:
    old = pending(created_at=NOW - timedelta(days=3))
    items = [pending(), pending(), pending(), old]
    repository = SimpleNamespace(list_unsent=AsyncMock(return_value=items), mark_sent=AsyncMock())
    sender = ScriptedSender(
        [DeliveryResult.SENT, DeliveryResult.UNDELIVERABLE, DeliveryResult.RETRY]
    )

    stats = await DeliverNotificationsUseCase(cast(Any, repository), sender).execute(now=NOW)

    assert (stats.sent, stats.skipped, stats.failed) == (1, 2, 1)
    marked = repository.mark_sent.await_args.args[0]
    # Отправленное, недоставляемое и устаревшее — отмечены; с временной ошибкой — нет
    assert marked == [items[0].notification.id, items[1].notification.id, old.notification.id]
