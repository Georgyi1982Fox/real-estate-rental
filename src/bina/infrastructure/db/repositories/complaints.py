"""Жалобы на объявления (TASK-106)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.complaints import HIDE_AFTER, TRUSTED_ACCOUNT_AGE_HOURS
from bina.infrastructure.db.models import Complaint, Listing, User


class ComplaintsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_today(self, user_id: UUID, now: datetime) -> int:
        """Сколько жалоб пользователь отправил за последние сутки."""
        query = select(func.count()).where(
            Complaint.user_id == user_id, Complaint.created_at > now - timedelta(days=1)
        )
        return int((await self._session.execute(query)).scalar_one())

    async def add(self, listing_id: UUID, user_id: UUID, reason: str, comment: str) -> bool:
        """Сохранить жалобу (повторная — обновляет причину); ``True`` — объявление скрыто.

        Жалоба, по которой модератор уже решил, остаётся закрытой: иначе те же люди скрывали бы
        объявление сразу после того, как модератор вернул его в поиск.
        """
        now = datetime.now(UTC)
        statement = (
            insert(Complaint)
            .values(listing_id=listing_id, user_id=user_id, reason=reason, comment=comment)
            .on_conflict_do_update(
                index_elements=["listing_id", "user_id"],
                set_={"reason": reason, "comment": comment, "created_at": now},
                where=Complaint.resolved_at.is_(None),
            )
        )
        await self._session.execute(statement)
        trusted_since = now - timedelta(hours=TRUSTED_ACCOUNT_AGE_HOURS)
        open_count = (
            await self._session.execute(
                select(func.count())
                .select_from(Complaint)
                .join(User, User.id == Complaint.user_id)
                .where(
                    Complaint.listing_id == listing_id,
                    Complaint.resolved_at.is_(None),
                    User.created_at <= trusted_since,
                )
            )
        ).scalar_one()
        if open_count < HIDE_AFTER:
            return False
        # Оплаченные и проверенные объявления не скрываются сами — решает модератор
        result = await self._session.execute(
            update(Listing)
            .where(
                Listing.id == listing_id,
                Listing.hidden_at.is_(None),
                Listing.is_verified.is_not(True),
                or_(Listing.promoted_until.is_(None), Listing.promoted_until <= now),
                or_(Listing.bump_until.is_(None), Listing.bump_until <= now),
            )
            .values(hidden_at=now)
            .returning(Listing.id)
        )
        return result.first() is not None
