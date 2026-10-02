"""AI-анализ фото объявлений (TASK-114): пачкой по расписанию и по запросу. Не коммитит."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from bina.application.photo_analysis import PhotoReport, photos_fingerprint
from bina.application.ports.photo_analyzer import IPhotoAnalyzer, PhotoAnalysisError
from bina.infrastructure.db.models import Listing, PhotoReportRecord
from bina.infrastructure.db.repositories.photo_reports import PhotoReportsRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PhotoStats:
    analyzed: int
    failed: int


class AnalyzePhotosUseCase:
    def __init__(
        self,
        repository: PhotoReportsRepository,
        analyzer: IPhotoAnalyzer,
        model: str = "",
        after_save: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._repository = repository
        self._analyzer = analyzer
        self._model = model
        self._after_save = after_save

    async def execute(self, limit: int) -> PhotoStats:
        """Разбирает фото до ``limit`` объявлений без разбора (новые первыми)."""
        analyzed = failed = 0
        for listing in await self._repository.listings_without_report(limit):
            try:
                await self._analyze(listing)
            except PhotoAnalysisError as exc:
                logger.warning("Photos not analyzed", listing_id=str(listing.id), error=str(exc))
                failed += 1
                continue
            analyzed += 1
            if self._after_save is not None:
                await self._after_save()
        return PhotoStats(analyzed=analyzed, failed=failed)

    async def report_for(self, listing: Listing) -> PhotoReportRecord:
        """Разбор объявления: сохранённый, если фото те же, иначе новый.

        Raises:
            PhotoAnalysisError: фото нет или AI не справился.
        """
        record = await self._repository.get(listing.id)
        if record is not None and record.photos_hash == photos_fingerprint(listing.images):
            return record
        return await self._analyze(listing)

    async def _analyze(self, listing: Listing) -> PhotoReportRecord:
        report: PhotoReport = await self._analyzer.analyze(listing.images or [])
        return await self._repository.save(
            listing, report, photos_fingerprint(listing.images), self._model, datetime.now(UTC)
        )
