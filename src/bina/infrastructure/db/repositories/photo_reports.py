"""AI-разборы фото объявлений (TASK-114)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.photo_analysis import PhotoReport
from bina.infrastructure.db.models import Listing, ListingStatus, PhotoReportRecord


class PhotoReportsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, listing_id: UUID) -> PhotoReportRecord | None:
        return await self._session.get(PhotoReportRecord, listing_id)

    async def listings_without_report(self, limit: int) -> list[Listing]:
        """Активные объявления с фото и без разбора — новые первыми."""
        has_report = select(PhotoReportRecord.listing_id).where(
            PhotoReportRecord.listing_id == Listing.id
        )
        query = (
            select(Listing)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                Listing.hidden_at.is_(None),
                func.json_array_length(Listing.images) > 0,
                ~has_report.exists(),
            )
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def save(
        self,
        listing: Listing,
        report: PhotoReport,
        photos_hash: str,
        model: str,
        now: datetime,
    ) -> PhotoReportRecord:
        """Сохраняет разбор (новый или вместо старого) и уровень ремонта у объявления."""
        record = await self.get(listing.id)
        if record is None:
            record = PhotoReportRecord(listing_id=listing.id, created_at=now)
            self._session.add(record)
        record.level = report.level
        record.issues = list(report.issues)
        record.summary_ru = report.summary.get("ru", "")
        record.summary_en = report.summary.get("en", "")
        record.summary_ka = report.summary.get("ka", "")
        record.photos_hash = photos_hash
        record.model = model
        record.updated_at = now
        listing.repair_level = report.level
        await self._session.flush()
        return record
