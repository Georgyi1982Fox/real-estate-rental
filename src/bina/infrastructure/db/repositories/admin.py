"""Минимальная админка владельца (TASK-110): статистика и очередь жалоб."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.daily_report import DailyReport
from bina.application.owner_listings import OWNER_SOURCE
from bina.infrastructure.db.models import (
    Agency,
    AIUsage,
    Complaint,
    Conversation,
    DailyReportRecord,
    District,
    Listing,
    ListingStatus,
    Payment,
    User,
    Verification,
    Viewing,
)
from bina.infrastructure.db.models.payments import PaymentStatus
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.db.repositories.listings import not_hidden_duplicate


@dataclass(frozen=True, slots=True)
class AdminStats:
    users: int
    users_week: int
    premium: int
    stars_total: Decimal
    stars_month: Decimal
    payments_month: int
    sources: list[tuple[str, int]]  # объявлений в поиске по источникам
    hidden: int  # скрыто жалобами или модератором
    open_complaints: int
    districts: list[tuple[str, int]]  # популярные районы: объявлений в поиске


@dataclass(frozen=True, slots=True)
class ComplaintCase:
    listing_id: UUID
    title: str
    url: str | None
    source: str
    complaints: int
    reasons: list[str]
    comments: list[str]
    hidden: bool


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _count(self, *conditions: ColumnElement[bool]) -> int:
        return int(
            (await self._session.execute(select(func.count()).where(*conditions))).scalar_one()
        )

    async def _stars(self, *conditions: ColumnElement[bool]) -> Decimal:
        query = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.SUCCESS, *conditions
        )
        return Decimal(str((await self._session.execute(query)).scalar_one()))

    async def stats(self, now: datetime) -> AdminStats:
        users = User.is_deleted.is_(False)
        active = _active_listings()
        month_ago = now - timedelta(days=30)
        sources = (
            await self._session.execute(
                select(Listing.source_name, func.count())
                .where(*active)
                .group_by(Listing.source_name)
                .order_by(func.count().desc())
            )
        ).all()
        districts = (
            await self._session.execute(
                select(District.name_ru, func.count(Listing.id))
                .join(Listing, Listing.district_id == District.id)
                .where(*active)
                .group_by(District.name_ru)
                .order_by(func.count(Listing.id).desc())
                .limit(5)
            )
        ).all()
        return AdminStats(
            users=await self._count(users),
            users_week=await self._count(users, User.created_at > now - timedelta(days=7)),
            premium=await self._premium(now),
            stars_total=await self._stars(),
            stars_month=await self._stars(Payment.created_at > month_ago),
            payments_month=await self._count(
                Payment.status == PaymentStatus.SUCCESS, Payment.created_at > month_ago
            ),
            sources=[(str(name), int(count)) for name, count in sources],
            hidden=await self._count(Listing.hidden_at.is_not(None), Listing.is_deleted.is_(False)),
            open_complaints=await self._count(Complaint.resolved_at.is_(None)),
            districts=[(str(name), int(count)) for name, count in districts],
        )

    async def _premium(self, now: datetime) -> int:
        return await self._count(
            User.is_deleted.is_(False),
            User.subscription_tier != SubscriptionTier.FREE,
            User.subscription_expires_at > now,
        )

    async def daily(self, now: datetime) -> DailyReport:
        """Ежедневный отчёт владельцу (TASK-041): за последние 24 часа."""
        since = now - timedelta(days=1)
        users = User.is_deleted.is_(False)
        active = _active_listings()
        paid = Payment.status == PaymentStatus.SUCCESS
        ai_requests = (
            await self._session.execute(
                select(func.coalesce(func.sum(AIUsage.count), 0)).where(AIUsage.day >= since.date())
            )
        ).scalar_one()
        return DailyReport(
            users=await self._count(users),
            users_new=await self._count(users, User.created_at > since),
            listings=await self._count(*active),
            listings_new=await self._count(*active, Listing.created_at > since),
            owner_listings_new=await self._count(
                Listing.source_name == OWNER_SOURCE,
                Listing.is_deleted.is_(False),
                Listing.created_at > since,
            ),
            agencies=await self._count(Agency.blocked_at.is_(None)),
            agencies_new=await self._count(Agency.created_at > since),
            chats_new=await self._count(Conversation.created_at > since),
            viewings_new=await self._count(Viewing.created_at > since),
            verifications_pending=await self._count(Verification.status == "pending"),
            open_complaints=await self._count(Complaint.resolved_at.is_(None)),
            payments=await self._count(paid, Payment.created_at > since),
            stars=await self._stars(Payment.created_at > since),
            premium=await self._premium(now),
            ai_requests=int(ai_requests),
        )

    async def claim_daily_report(self, day: date) -> bool:
        """Застолбить отчёт за день: ``True`` — ещё не отправляли, отправляем мы."""
        result = await self._session.execute(
            pg_insert(DailyReportRecord)
            .values(day=day)
            .on_conflict_do_nothing(index_elements=[DailyReportRecord.day])
            .returning(DailyReportRecord.day)
        )
        return result.first() is not None

    async def complaint_queue(self, limit: int) -> list[ComplaintCase]:
        """Объявления с открытыми жалобами: сначала с большим числом жалоб."""
        open_complaints = Complaint.resolved_at.is_(None)
        rows = (
            await self._session.execute(
                select(Listing, func.count(Complaint.user_id))
                .join(Complaint, Complaint.listing_id == Listing.id)
                .where(open_complaints)
                .group_by(Listing.id)
                .order_by(func.count(Complaint.user_id).desc(), func.max(Complaint.created_at))
                .limit(limit)
            )
        ).all()
        cases = []
        for listing, count in rows:
            details = (
                await self._session.execute(
                    select(Complaint.reason, Complaint.comment).where(
                        Complaint.listing_id == listing.id, open_complaints
                    )
                )
            ).all()
            cases.append(
                ComplaintCase(
                    listing_id=listing.id,
                    title=listing.title_ru or listing.title_en or listing.title_ka or "",
                    url=listing.url or None,
                    source=listing.source_name,
                    complaints=int(count),
                    reasons=[reason for reason, _ in details],
                    comments=[comment for _, comment in details if comment],
                    hidden=listing.hidden_at is not None,
                )
            )
        return cases

    async def _resolve(self, listing_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(Complaint)
            .where(Complaint.listing_id == listing_id, Complaint.resolved_at.is_(None))
            .values(resolved_at=now)
        )

    async def hide(self, listing_id: UUID, now: datetime | None = None) -> None:
        """Скрыть объявление (подтвердить жалобы)."""
        now = now or datetime.now(UTC)
        await self._session.execute(
            update(Listing).where(Listing.id == listing_id).values(hidden_at=now)
        )
        await self._resolve(listing_id, now)

    async def restore(self, listing_id: UUID, now: datetime | None = None) -> None:
        """Вернуть объявление в поиск (жалобы отклонены)."""
        now = now or datetime.now(UTC)
        await self._session.execute(
            update(Listing).where(Listing.id == listing_id).values(hidden_at=None)
        )
        await self._resolve(listing_id, now)


def _active_listings() -> list[ColumnElement[bool]]:
    """Объявления в поиске: активные, не удалённые, не скрытые, не дубликаты."""
    return [
        Listing.status == ListingStatus.ACTIVE,
        Listing.is_deleted.is_(False),
        Listing.hidden_at.is_(None),
        not_hidden_duplicate(),
    ]
