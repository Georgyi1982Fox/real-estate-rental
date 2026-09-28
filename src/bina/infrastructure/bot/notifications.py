"""Отправка уведомлений в Telegram (TASK-028).

Сообщение: что случилось (новая квартира по поиску / цена снижена), заголовок,
цена, комнаты, площадь и кнопка «Открыть» — квартира в Mini App (если задан
``BOT_MINI_APP_URL``) или объявление на сайте-источнике.
"""

import asyncio
from html import escape

import structlog
from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from bina.application.ports.notification_sender import DeliveryResult, INotificationSender
from bina.application.repositories.notifications import PendingNotification
from bina.infrastructure.bot.formatters import (
    MAX_TITLE_LENGTH,
    format_number,
    format_price,
    listing_title,
    truncate,
)
from bina.infrastructure.bot.texts import t, ui_language
from bina.infrastructure.db.models import Listing, NotificationType

logger = structlog.get_logger(__name__)

# Пауза между сообщениями: лимит Telegram ~30 сообщений в секунду
SEND_INTERVAL_SECONDS = 0.05
MAX_RETRY_AFTER_SECONDS = 30


def render_notification(
    pending: PendingNotification, mini_app_url: str | None
) -> tuple[str, InlineKeyboardMarkup | None] | None:
    """Текст и кнопка уведомления; ``None``, если отправлять нечего."""
    notification = pending.notification
    language = pending.language
    if notification.type == NotificationType.SYSTEM.value:
        texts = notification.text or {}
        body = texts.get(language) or texts.get(ui_language(language)) or texts.get("en")
        return (escape(str(body)), None) if body else None

    listing = pending.listing
    if listing is None or listing.is_deleted:
        return None
    card = _listing_card(listing, language)
    if notification.type == NotificationType.PRICE_DROP.value:
        old = notification.old_price if notification.old_price is not None else listing.price
        new = notification.new_price if notification.new_price is not None else listing.price
        text = t(
            language,
            "notify_price_drop",
            old=format_price(old, listing.currency),
            new=format_price(new, listing.currency),
            listing=card,
        )
    elif pending.search_name:
        text = t(language, "notify_new_listing", search=escape(pending.search_name), listing=card)
    else:
        text = t(language, "notify_new_listing_no_search", listing=card)
    return text, _open_button(listing, language, mini_app_url)


def _listing_card(listing: Listing, language: str) -> str:
    title = escape(truncate(listing_title(listing, language), MAX_TITLE_LENGTH))
    details = t(
        language,
        "notify_details",
        price=format_price(listing.price, listing.currency),
        rooms=listing.rooms,
        area=format_number(listing.area),
    )
    return f"<b>{title}</b>\n{details}"


def _open_button(
    listing: Listing, language: str, mini_app_url: str | None
) -> InlineKeyboardMarkup | None:
    text = t(language, "notify_open")
    if mini_app_url:
        url = f"{mini_app_url.rstrip('/')}/listing/{listing.id}"
        button = InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))
    elif listing.url:
        button = InlineKeyboardButton(text=text, url=listing.url)
    else:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


class TelegramNotificationSender(INotificationSender):
    """:class:`INotificationSender` через Bot API."""

    def __init__(
        self,
        bot: Bot,
        mini_app_url: str | None = None,
        send_interval: float = SEND_INTERVAL_SECONDS,
    ) -> None:
        self._bot = bot
        self._mini_app_url = mini_app_url
        self._send_interval = send_interval

    async def send(self, pending: PendingNotification) -> DeliveryResult:
        """Отправить одно уведомление."""
        rendered = render_notification(pending, self._mini_app_url)
        if rendered is None:
            return DeliveryResult.UNDELIVERABLE
        text, keyboard = rendered
        try:
            await self._bot.send_message(
                chat_id=pending.telegram_id,
                text=text,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            # Пользователь заблокировал бота или чат недоступен — повторять бессмысленно
            logger.info(
                "Notification undeliverable", telegram_id=pending.telegram_id, error=str(exc)
            )
            return DeliveryResult.UNDELIVERABLE
        except TelegramRetryAfter as exc:
            await asyncio.sleep(min(exc.retry_after, MAX_RETRY_AFTER_SECONDS))
            return DeliveryResult.RETRY
        except (TelegramNetworkError, TelegramServerError) as exc:
            logger.warning("Notification send failed", error=str(exc))
            return DeliveryResult.RETRY
        await asyncio.sleep(self._send_interval)
        return DeliveryResult.SENT
