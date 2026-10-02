"""Заявки на проверку собственника (TASK-098)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.promotion import VerificationStatus
from bina.infrastructure.db.models import Verification


class VerificationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, verification_id: UUID) -> Verification | None:
        return await self._session.get(Verification, verification_id)

    async def pending_for(self, listing_id: UUID) -> Verification | None:
        query = select(Verification).where(
            Verification.listing_id == listing_id,
            Verification.status == VerificationStatus.PENDING,
        )
        return (await self._session.execute(query)).scalars().first()

    async def pending_listing_ids(self, user_id: UUID) -> set[UUID]:
        query = select(Verification.listing_id).where(
            Verification.user_id == user_id,
            Verification.status == VerificationStatus.PENDING,
        )
        return set((await self._session.execute(query)).scalars().all())

    async def add(
        self, listing_id: UUID, user_id: UUID, file_id: str, file_kind: str, now: datetime
    ) -> Verification:
        verification = Verification(
            listing_id=listing_id,
            user_id=user_id,
            status=VerificationStatus.PENDING,
            file_id=file_id,
            file_kind=file_kind,
            created_at=now,
            updated_at=now,
        )
        self._session.add(verification)
        await self._session.flush()
        return verification

    async def decide(
        self, verification: Verification, status: VerificationStatus, now: datetime
    ) -> None:
        """Решение администратора; документ (file_id) больше не храним."""
        verification.status = status
        verification.decided_at = now
        verification.updated_at = now
        verification.file_id = None
        await self._session.flush()
