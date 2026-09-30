"""Сохранённые поиски и уведомления в PostgreSQL (TASK-028)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bina.application.repositories.notifications import (
    INotificationsRepository,
    ISavedSearchesRepository,
    PendingNotification,
)
from bina.infrastructure.db.models import (
    Notification,
    NotificationType,
    SavedSearch,
    User,
)
from bina.infrastructure.db.repositories.users import premium_access_now


class SavedSearchesRepository(ISavedSearchesRepository):
    """Сохранённые поиски пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user(self, user_id: UUID) -> list[SavedSearch]:
        """Поиски пользователя (новые сверху)."""
        query = (
            select(SavedSearch)
            .where(SavedSearch.user_id == user_id)
            .order_by(SavedSearch.created_at.desc())
        )
        return list((await self._session.execute(query)).scalars().all())

    async def get(self, user_id: UUID, search_id: UUID) -> SavedSearch | None:
        """Поиск пользователя по ID (чужой не отдаётся)."""
        query = select(SavedSearch).where(
            SavedSearch.id == search_id, SavedSearch.user_id == user_id
        )
        return (await self._session.execute(query)).scalar_one_or_none()

    async def count_by_user(self, user_id: UUID) -> int:
        """Количество поисков пользователя."""
        query = select(func.count()).select_from(SavedSearch).where(SavedSearch.user_id == user_id)
        return int((await self._session.execute(query)).scalar_one())

    async def create(self, user_id: UUID, **fields: Any) -> SavedSearch:
        """Сохранить поиск."""
        now = datetime.now(UTC)
        search = SavedSearch(user_id=user_id, notify_since=now, last_viewed_at=now, **fields)
        self._session.add(search)
        await self._session.flush()
        await self._session.refresh(search)
        return search

    async def delete(self, user_id: UUID, search_id: UUID) -> bool:
        """Удалить поиск; ``False``, если его не было."""
        result = await self._session.execute(
            delete(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == user_id)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def list_notifiable(self) -> list[SavedSearch]:
        """Поиски с включёнными уведомлениями (владельцы не удалены)."""
        query = (
            select(SavedSearch)
            .join(User, User.id == SavedSearch.user_id)
            .where(SavedSearch.notify.is_(True), User.is_deleted.is_(False))
        )
        return list((await self._session.execute(query)).scalars().all())


class NotificationsRepository(INotificationsRepository):
    """Уведомления пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _insert(self, values: dict[str, Any], index: list[str], kind: str) -> bool:
        query = (
            insert(Notification)
            .values(**values)
            .on_conflict_do_nothing(index_elements=index, index_where=text(f"type = '{kind}'"))
            .returning(Notification.id)
        )
        return (await self._session.execute(query)).scalar_one_or_none() is not None

    async def add_new_listing(self, user_id: UUID, listing_id: UUID, search_id: UUID) -> bool:
        """Уведомление о новой квартире; ``False``, если такое уже есть."""
        kind = NotificationType.NEW_LISTING.value
        return await self._insert(
            {"user_id": user_id, "type": kind, "listing_id": listing_id, "search_id": search_id},
            ["user_id", "listing_id"],
            kind,
        )

    async def add_price_drop(
        self, user_id: UUID, listing_id: UUID, old_price: Decimal, new_price: Decimal
    ) -> bool:
        """Уведомление о снижении цены; ``False``, если о снижении до этой цены уже сообщали."""
        kind = NotificationType.PRICE_DROP.value
        return await self._insert(
            {
                "user_id": user_id,
                "type": kind,
                "listing_id": listing_id,
                "old_price": old_price,
                "new_price": new_price,
            },
            ["user_id", "listing_id", "new_price"],
            kind,
        )

    async def list_for_user(
        self, user_id: UUID, *, unread_only: bool, limit: int, offset: int
    ) -> list[Notification]:
        """Уведомления пользователя (новые сверху) с объявлением и поиском."""
        query = (
            select(Notification)
            .where(*self._user_conditions(user_id, unread_only))
            .options(selectinload(Notification.listing), selectinload(Notification.search))
            .order_by(Notification.created_at.desc(), Notification.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def count_for_user(self, user_id: UUID, *, unread_only: bool) -> int:
        """Количество уведомлений пользователя."""
        query = (
            select(func.count())
            .select_from(Notification)
            .where(*self._user_conditions(user_id, unread_only))
        )
        return int((await self._session.execute(query)).scalar_one())

    @staticmethod
    def _user_conditions(user_id: UUID, unread_only: bool) -> list[Any]:
        conditions: list[Any] = [Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.is_read.is_(False))
        return conditions

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> bool:
        """Отметить прочитанным; ``False``, если уведомления нет (или оно чужое)."""
        result = await self._session.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def mark_all_read(self, user_id: UUID) -> None:
        """Отметить прочитанными все уведомления пользователя."""
        await self._session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )

    async def list_unsent(
        self, limit: int, free_created_before: datetime | None = None
    ) -> list[PendingNotification]:
        """Неотправленные в Telegram уведомления (старые первыми).

        ``free_created_before``: без Premium — только созданные до этого момента
        (кроме служебных).
        """
        query = (
            select(Notification, User.telegram_id, User.language)
            .join(User, User.id == Notification.user_id)
            .where(Notification.sent_at.is_(None), User.is_deleted.is_(False))
            .options(selectinload(Notification.listing), selectinload(Notification.search))
            .order_by(Notification.created_at)
            .limit(limit)
        )
        if free_created_before is not None:
            # Служебные сообщения (о подписке) — без задержки
            query = query.where(
                or_(
                    premium_access_now(),
                    Notification.type == NotificationType.SYSTEM.value,
                    Notification.created_at <= free_created_before,
                )
            )
        rows = (await self._session.execute(query)).all()
        return [
            PendingNotification(
                notification=notification,
                telegram_id=int(telegram_id),
                language=language,
                listing=notification.listing,
                search_name=notification.search.name if notification.search else None,
            )
            for notification, telegram_id, language in rows
        ]

    async def mark_sent(self, notification_ids: list[UUID]) -> None:
        """Отметить отправленными (или пропущенными)."""
        if notification_ids:
            await self._session.execute(
                update(Notification)
                .where(Notification.id.in_(notification_ids))
                .values(sent_at=datetime.now(UTC))
            )
