"""Порты хранилищ сохранённых поисков и уведомлений (TASK-028)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.infrastructure.db.models import Listing, Notification, SavedSearch


@dataclass(frozen=True, slots=True)
class PriceDrop:
    """Объявление из избранного пользователя, которое подешевело."""

    user_id: UUID
    listing: Listing
    old_price: Decimal


@dataclass(frozen=True, slots=True)
class PendingNotification:
    """Уведомление, ещё не отправленное в Telegram, с данными для сообщения."""

    notification: Notification
    telegram_id: int
    language: str
    listing: Listing | None
    search_name: str | None


class ISavedSearchesRepository(Protocol):
    """Сохранённые поиски."""

    async def list_notifiable(self) -> list[SavedSearch]:
        """Поиски с включёнными уведомлениями."""
        ...


class IListingMatchesRepository(Protocol):
    """Выборки объявлений для уведомлений."""

    async def search_created_since(
        self, filters: ListingSearchFilters, since: datetime, limit: int
    ) -> list[Listing]:
        """Активные объявления под фильтры, появившиеся после ``since`` (новые сверху)."""
        ...

    async def favorite_price_drops(self, since: datetime) -> list[PriceDrop]:
        """Подешевевшие после ``since`` объявления из избранного пользователей."""
        ...


class INotificationsRepository(Protocol):
    """Уведомления."""

    async def add_new_listing(self, user_id: UUID, listing_id: UUID, search_id: UUID) -> bool:
        """Уведомление о новой квартире; ``False``, если такое уже есть."""
        ...

    async def add_price_drop(
        self, user_id: UUID, listing_id: UUID, old_price: Decimal, new_price: Decimal
    ) -> bool:
        """Уведомление о снижении цены; ``False``, если о снижении до этой цены уже сообщали."""
        ...

    async def list_unsent(self, limit: int) -> list[PendingNotification]:
        """Неотправленные в Telegram уведомления (старые первыми)."""
        ...

    async def mark_sent(self, notification_ids: list[UUID]) -> None:
        """Отметить отправленными (или пропущенными)."""
        ...
