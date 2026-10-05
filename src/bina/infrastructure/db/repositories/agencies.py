"""Агентства, их статистика и ежедневное поднятие Premium-объявлений (TASK-100)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bina.application.chat import ViewingStatus
from bina.application.owner_listings import OWNER_SOURCE
from bina.infrastructure.db.models import (
    Agency,
    Conversation,
    Favorite,
    Listing,
    ListingStat,
    ListingStatus,
    Viewing,
)

# Статистика в кабинете — за последние 30 дней
STATS_DAYS = 30


@dataclass(frozen=True, slots=True)
class ListingStats:
    listing: Listing
    views: int = 0
    contacts: int = 0
    chats: int = 0
    viewings: int = 0
    favorites: int = 0


class AgenciesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, agency_id: UUID) -> Agency | None:
        return await self._session.get(Agency, agency_id)

    async def for_user(self, user_id: UUID) -> Agency | None:
        query = select(Agency).where(Agency.user_id == user_id)
        return (await self._session.execute(query)).scalar_one_or_none()

    async def create(
        self, user_id: UUID, name: str, phone: str | None, description: str, now: datetime
    ) -> Agency:
        agency = Agency(
            user_id=user_id,
            name=name,
            phone=phone,
            description=description,
            created_at=now,
            updated_at=now,
        )
        self._session.add(agency)
        await self._session.flush()
        return agency

    async def save(self, agency: Agency, now: datetime) -> None:
        agency.updated_at = now
        await self._session.flush()

    async def block(self, agency: Agency, now: datetime) -> int:
        """Блокировка: агентство и все его объявления в поиске скрыты. Сколько скрыто."""
        agency.blocked_at = now
        result = await self._session.execute(
            update(Listing)
            .where(
                Listing.owner_user_id == agency.user_id,
                Listing.source_name == OWNER_SOURCE,
                Listing.hidden_at.is_(None),
            )
            .values(hidden_at=now)
            .returning(Listing.id)
        )
        return len(result.all())

    async def listings(self, user_id: UUID, active_only: bool = False) -> list[Listing]:
        """Объявления агентства: новые сверху."""
        query = (
            select(Listing)
            .options(selectinload(Listing.district))
            .where(
                Listing.owner_user_id == user_id,
                Listing.source_name == OWNER_SOURCE,
                Listing.is_deleted.is_(False),
            )
            .order_by(Listing.created_at.desc())
        )
        if active_only:
            query = query.where(Listing.status == ListingStatus.ACTIVE, Listing.hidden_at.is_(None))
        return list((await self._session.execute(query)).scalars().all())

    async def stats(self, user_id: UUID, today: date) -> list[ListingStats]:
        """Статистика объявлений агентства за ``STATS_DAYS`` дней."""
        listings = await self.listings(user_id)
        if not listings:
            return []
        ids = [listing.id for listing in listings]
        since_day = today - timedelta(days=STATS_DAYS)
        since = datetime.combine(since_day, time(), tzinfo=UTC)
        counters = {
            row.listing_id: (int(row.views), int(row.contacts))
            for row in await self._session.execute(
                select(
                    ListingStat.listing_id,
                    func.sum(ListingStat.views).label("views"),
                    func.sum(ListingStat.contacts).label("contacts"),
                )
                .where(ListingStat.listing_id.in_(ids), ListingStat.day >= since_day)
                .group_by(ListingStat.listing_id)
            )
        }
        chats = await self._count(Conversation.listing_id, ids, Conversation.created_at >= since)
        viewings = await self._count(
            Viewing.listing_id,
            ids,
            Viewing.created_at >= since,
            Viewing.status != ViewingStatus.DECLINED,
        )
        favorites = await self._count(Favorite.listing_id, ids)
        return [
            ListingStats(
                listing=listing,
                views=counters.get(listing.id, (0, 0))[0],
                contacts=counters.get(listing.id, (0, 0))[1],
                chats=chats.get(listing.id, 0),
                viewings=viewings.get(listing.id, 0),
                favorites=favorites.get(listing.id, 0),
            )
            for listing in listings
        ]

    async def _count(self, column: object, ids: list[UUID], *conditions: object) -> dict[UUID, int]:
        query = (
            select(column, func.count())  # type: ignore[call-overload]
            .where(column.in_(ids), *conditions)  # type: ignore[attr-defined]
            .group_by(column)
        )
        return {listing_id: int(count) for listing_id, count in await self._session.execute(query)}

    # --- Premium-объявления

    async def bump_candidates(self, now: datetime) -> list[Listing]:
        """Premium-объявления в поиске (поднимать или нет — решает bump_due)."""
        query = (
            select(Listing)
            .where(
                Listing.bump_until > now,
                Listing.status == ListingStatus.ACTIVE,
                Listing.hidden_at.is_(None),
                Listing.is_deleted.is_(False),
            )
            .order_by(Listing.bumped_at.asc().nulls_first(), Listing.id)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def bump(self, listing: Listing, now: datetime) -> None:
        """Поднять наверх «новых»: как будто объявление только что обновили."""
        listing.bumped_at = now
        listing.source_updated_at = now
        await self._session.flush()

    async def set_bump(self, listing: Listing, until: datetime) -> None:
        listing.bump_until = until
        await self._session.flush()


class ListingStatsRepository:
    """Счётчики просмотров и «Написать» объявлений хозяев и агентств."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, listing: Listing, day: date, *, view: bool = False) -> None:
        """+1 просмотр (``view``) или +1 обращение (у любого объявления: счётчик просмотров
        видят все, статистику обращений — хозяин и агентство)."""
        views, contacts = (1, 0) if view else (0, 1)
        statement = pg_insert(ListingStat).values(
            listing_id=listing.id, day=day, views=views, contacts=contacts
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[ListingStat.listing_id, ListingStat.day],
                set_={
                    "views": ListingStat.views + statement.excluded.views,
                    "contacts": ListingStat.contacts + statement.excluded.contacts,
                    "updated_at": func.now(),
                },
            )
        )

    async def total_views(self, listing_id: UUID) -> int:
        """Сколько раз объявление открывали на Bina.ai (сайт, приложение, бот)."""
        query = select(func.coalesce(func.sum(ListingStat.views), 0)).where(
            ListingStat.listing_id == listing_id
        )
        return int((await self._session.execute(query)).scalar_one())
