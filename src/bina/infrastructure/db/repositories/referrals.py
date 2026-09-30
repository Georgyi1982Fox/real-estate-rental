"""Приглашения друзей (TASK-108)."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.referrals import new_code
from bina.application.subscriptions import is_premium
from bina.application.use_cases.referrals import Friend
from bina.infrastructure.db.models import Notification, NotificationType, Payment, User
from bina.infrastructure.db.models.payments import PaymentStatus
from bina.infrastructure.db.models.users import SubscriptionTier

CODE_ATTEMPTS = 5


class ReferralsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def code_for(self, user: User) -> str:
        """Код приглашения пользователя (создаётся при первом запросе)."""
        if user.referral_code:
            return user.referral_code
        for _ in range(CODE_ATTEMPTS):
            code = new_code()
            try:
                async with self._session.begin_nested():
                    await self._session.execute(
                        update(User)
                        .where(User.id == user.id, User.referral_code.is_(None))
                        .values(referral_code=code)
                    )
            except IntegrityError:
                continue  # такой код уже есть — пробуем другой
            await self._session.refresh(user, attribute_names=["referral_code"])
            if user.referral_code:
                return user.referral_code
        raise RuntimeError("could not generate a referral code")

    async def by_code(self, code: str) -> User | None:
        query = select(User).where(User.referral_code == code, User.is_deleted.is_(False))
        return (await self._session.execute(query)).scalar_one_or_none()

    async def set_referrer(self, user: User, referrer: User) -> bool:
        """Запомнить, кто пригласил; ``False`` — нельзя (сам себя, уже есть или уже платил)."""
        if referrer.id == user.id or user.referred_by is not None:
            return False
        if await self.paid_count(user.id):
            return False
        await self._session.execute(
            update(User).where(User.id == user.id).values(referred_by=referrer.id)
        )
        user.referred_by = referrer.id
        return True

    async def discount_eligible(self, user: User) -> bool:
        """Скидка другу: приглашён и ещё ни разу не платил."""
        return user.referred_by is not None and await self.paid_count(user.id) == 0

    async def stats(self, user_id: UUID, since: datetime) -> tuple[int, int, int]:
        """(приглашено всего, наград всего, наград с ``since``)."""
        query = select(
            func.count(),
            func.count(User.referral_rewarded_at),
            func.count().filter(User.referral_rewarded_at >= since),
        ).where(User.referred_by == user_id)
        invited, rewarded, recent = (await self._session.execute(query)).one()
        return int(invited), int(rewarded), int(recent)

    # --- IReferralRewardsRepository

    async def friend(self, user_id: UUID) -> Friend:
        referred_by, rewarded_at = (
            await self._session.execute(
                select(User.referred_by, User.referral_rewarded_at).where(User.id == user_id)
            )
        ).one()
        return Friend(user_id=user_id, referred_by=referred_by, rewarded=rewarded_at is not None)

    async def paid_count(self, user_id: UUID) -> int:
        query = select(func.count()).where(
            Payment.user_id == user_id, Payment.status == PaymentStatus.SUCCESS
        )
        return int((await self._session.execute(query)).scalar_one())

    async def rewards_since(self, referrer_id: UUID, since: datetime) -> int:
        return (await self.stats(referrer_id, since))[2]

    async def extend_premium(self, user_id: UUID, days: int, now: datetime) -> datetime:
        user = (await self._session.execute(select(User).where(User.id == user_id))).scalar_one()
        start = user.subscription_expires_at if is_premium(user, now) else now
        assert start is not None
        until = start + timedelta(days=days)
        tier = user.subscription_tier if is_premium(user, now) else SubscriptionTier.NOMAD
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(subscription_tier=tier, subscription_expires_at=until)
        )
        return until

    async def mark_rewarded(self, friend_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(User).where(User.id == friend_id).values(referral_rewarded_at=now)
        )

    async def notify(self, user_id: UUID, texts: dict[str, str]) -> None:
        self._session.add(
            Notification(user_id=user_id, type=NotificationType.SYSTEM.value, text=texts)
        )
