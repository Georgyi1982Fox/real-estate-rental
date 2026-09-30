"""Награда за приглашённого друга (TASK-108).

Вызывается после успешной оплаты. Если это первая оплата приглашённого и
пригласившему в этом месяце ещё можно давать награды — продлевает ему Premium
на ``REWARD_DAYS`` дней и пишет об этом. Не коммитит.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from bina.application.referrals import MONTHLY_REWARDS, REWARD_DAYS, REWARD_TEXTS, month_start

DATE_FORMAT = "%d.%m.%Y"


@dataclass(frozen=True, slots=True)
class Friend:
    user_id: UUID
    referred_by: UUID | None
    rewarded: bool


class IReferralRewardsRepository(Protocol):
    async def friend(self, user_id: UUID) -> Friend: ...

    async def paid_count(self, user_id: UUID) -> int: ...

    async def rewards_since(self, referrer_id: UUID, since: datetime) -> int: ...

    async def extend_premium(self, user_id: UUID, days: int, now: datetime) -> datetime: ...

    async def mark_rewarded(self, friend_id: UUID, now: datetime) -> None: ...

    async def notify(self, user_id: UUID, texts: dict[str, str]) -> None: ...


class RewardReferrerUseCase:
    def __init__(self, repository: IReferralRewardsRepository) -> None:
        self._repository = repository

    async def execute(self, user_id: UUID, now: datetime) -> bool:
        """``True`` — пригласивший получил награду."""
        friend = await self._repository.friend(user_id)
        if friend.referred_by is None or friend.rewarded:
            return False
        # Награда — только за первую оплату друга (платёж уже записан)
        if await self._repository.paid_count(user_id) != 1:
            return False
        referrer = friend.referred_by
        if await self._repository.rewards_since(referrer, month_start(now)) >= MONTHLY_REWARDS:
            return False
        until = await self._repository.extend_premium(referrer, REWARD_DAYS, now)
        await self._repository.mark_rewarded(user_id, now)
        date = f"{until:{DATE_FORMAT}}"
        await self._repository.notify(
            referrer,
            {lang: text.format(days=REWARD_DAYS, date=date) for lang, text in REWARD_TEXTS.items()},
        )
        return True
