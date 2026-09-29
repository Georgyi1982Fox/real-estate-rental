"""Уведомления о новых квартирах и снижении цен (TASK-028).

Запускаются после каждого парсинга:

1. :class:`CreateNotificationsUseCase` сверяет новые объявления с сохранёнными
   поисками (``notify=True``) и избранное с изменениями цен. Повторы отсекает
   уникальный индекс в БД, поэтому запуск можно повторять сколько угодно.
2. :class:`DeliverNotificationsUseCase` отправляет неотправленные уведомления
   в Telegram. Уведомления старше ``max_age`` не отправляются (бот был выключен —
   не засыпаем пользователя старыми квартирами), но остаются в списке Mini App.

Premium (TASK-085): новые квартиры приходят сразу после парсинга, бесплатному
тарифу — через ``free_delay`` (3 часа); «цена снижена» — только Premium.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

from bina.application.dtos.listing_search import search_filters
from bina.application.ports.notification_sender import DeliveryResult, INotificationSender
from bina.application.repositories.notifications import (
    IListingMatchesRepository,
    INotificationsRepository,
    ISavedSearchesRepository,
)

logger = structlog.get_logger(__name__)

# Сколько новых квартир по одному поиску проверять за запуск (самые свежие)
MATCHES_PER_SEARCH = 20
# За какой период искать снижения цен в избранном
PRICE_DROP_LOOKBACK = timedelta(days=7)
# Уведомления старше этого в Telegram не отправляются
MAX_DELIVERY_AGE = timedelta(days=2)
# Задержка уведомлений бесплатного тарифа: Premium узнаёт о квартире раньше (TASK-085)
FREE_DELIVERY_DELAY = timedelta(hours=3)


@dataclass(frozen=True, slots=True)
class CreatedNotifications:
    """Сколько уведомлений создано."""

    new_listings: int
    price_drops: int


@dataclass(frozen=True, slots=True)
class DeliveryStats:
    """Итог отправки."""

    sent: int
    skipped: int
    failed: int


class CreateNotificationsUseCase:
    """Создаёт уведомления «новая квартира по поиску» и «цена снижена»."""

    def __init__(
        self,
        searches: ISavedSearchesRepository,
        listings: IListingMatchesRepository,
        notifications: INotificationsRepository,
    ) -> None:
        self._searches = searches
        self._listings = listings
        self._notifications = notifications

    async def execute(self, now: datetime | None = None) -> CreatedNotifications:
        """Не коммитит: транзакцией управляет вызывающий код."""
        now = now or datetime.now(UTC)
        new_listings = 0
        for search in await self._searches.list_notifiable():
            filters = search_filters(
                district_ids=search.all_district_ids,
                price_min=search.price_min,
                price_max=search.price_max,
                rooms=search.rooms,
            )
            matches = await self._listings.search_created_since(
                filters, search.notify_since, MATCHES_PER_SEARCH
            )
            for listing in matches:
                if await self._notifications.add_new_listing(search.user_id, listing.id, search.id):
                    new_listings += 1

        price_drops = 0
        drops = await self._listings.favorite_price_drops(
            now - PRICE_DROP_LOOKBACK, premium_only=True
        )
        for drop in drops:
            if await self._notifications.add_price_drop(
                drop.user_id, drop.listing.id, drop.old_price, drop.listing.price
            ):
                price_drops += 1

        logger.info("Notifications created", new_listings=new_listings, price_drops=price_drops)
        return CreatedNotifications(new_listings=new_listings, price_drops=price_drops)


class DeliverNotificationsUseCase:
    """Отправляет неотправленные уведомления."""

    def __init__(
        self,
        notifications: INotificationsRepository,
        sender: INotificationSender,
        max_age: timedelta = MAX_DELIVERY_AGE,
        free_delay: timedelta = FREE_DELIVERY_DELAY,
    ) -> None:
        self._notifications = notifications
        self._sender = sender
        self._max_age = max_age
        self._free_delay = free_delay

    async def execute(self, limit: int = 100, now: datetime | None = None) -> DeliveryStats:
        """Не коммитит: транзакцией управляет вызывающий код."""
        now = now or datetime.now(UTC)
        done = []
        sent = skipped = failed = 0
        for pending in await self._notifications.list_unsent(limit, now - self._free_delay):
            if now - pending.notification.created_at > self._max_age:
                done.append(pending.notification.id)
                skipped += 1
                continue
            result = await self._sender.send(pending)
            if result is DeliveryResult.RETRY:
                failed += 1
                continue
            done.append(pending.notification.id)
            if result is DeliveryResult.SENT:
                sent += 1
            else:
                skipped += 1
        if done:
            await self._notifications.mark_sent(done)
        logger.info("Notifications delivered", sent=sent, skipped=skipped, failed=failed)
        return DeliveryStats(sent=sent, skipped=skipped, failed=failed)
