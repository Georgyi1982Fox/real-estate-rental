"""AI-разбор фото объявления: ремонт и видимые дефекты (TASK-114).

Всем — уровень ремонта (он же ``repair_level`` в объявлении). Premium — какие проблемы
видны и короткий вывод на языке пользователя. Объявления разбираются по расписанию;
если разбора ещё нет (или фото поменялись), для Premium он делается сразу.
"""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from bina.application.photo_analysis import (
    issue_label,
    level_label,
    photos_fingerprint,
    photos_for_analysis,
)
from bina.application.ports.photo_analyzer import IPhotoAnalyzer, PhotoAnalysisError
from bina.application.subscriptions import has_premium_access
from bina.application.use_cases.analyze_photos import AnalyzePhotosUseCase
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import get_listing_or_404, not_found
from bina.infrastructure.db.models import PhotoReportRecord
from bina.infrastructure.db.repositories.photo_reports import PhotoReportsRepository
from bina.infrastructure.db.repositories.users import take_ai_request
from bina.infrastructure.llm.photo_analyzer import (
    create_photo_analyzer,
    photo_analysis_configured,
)

router = APIRouter(prefix="/api/listings", tags=["photo-report"])

# Разборов по запросу на пользователя в день (расход на AI), вместе с AI-помощником
DAILY_LIMIT = 30


class PhotoIssueOut(BaseModel):
    code: str
    label: str


class PhotoReportOut(BaseModel):
    """Всем: ``level``. Premium: ``issues`` и ``summary``; иначе ``premium_required``."""

    level: Literal["excellent", "good", "needs_repair"]
    level_label: str = Field(description="«Хороший ремонт» на языке пользователя")
    issues: list[PhotoIssueOut] = Field(default_factory=list)
    summary: str = ""
    analyzed_at: datetime
    premium_required: bool = False


def _out(record: PhotoReportRecord, language: str, premium: bool) -> PhotoReportOut:
    level = record.level
    out = PhotoReportOut(
        level=level,  # type: ignore[arg-type]
        level_label=level_label(level, language),
        analyzed_at=record.updated_at,
        premium_required=not premium,
    )
    if premium:
        out.issues = [
            PhotoIssueOut(code=code, label=issue_label(code, language))
            for code in record.issues
            if issue_label(code, language)
        ]
        summaries = {"ru": record.summary_ru, "en": record.summary_en, "ka": record.summary_ka}
        out.summary = summaries.get(language) or record.summary_en or record.summary_ru
    return out


def _analyzer(request: Request) -> IPhotoAnalyzer | None:
    """В тестах — ``app.state.photo_analyzer``; без ключа AI — None."""
    injected: IPhotoAnalyzer | None = getattr(request.app.state, "photo_analyzer", None)
    if injected is not None:
        return injected
    return create_photo_analyzer() if photo_analysis_configured() else None


@router.get("/{listing_id}/photo-report", response_model=PhotoReportOut)
async def photo_report(
    listing_id: str, request: Request, user: CurrentUserDep, session: SessionDep
) -> PhotoReportOut:
    """Разбор фото; 404 — фото нет (или разбора ещё нет, а пользователь без Premium)."""
    listing = await get_listing_or_404(session, listing_id)
    if not photos_for_analysis(listing.images):
        raise not_found("No photos")
    now = datetime.now(UTC)
    premium = has_premium_access(user, now)
    repository = PhotoReportsRepository(session)
    record = await repository.get(listing.id)
    if not premium:
        if record is None:
            raise not_found("Photos not analyzed yet")
        return _out(record, user.language, premium=False)

    analyzer = _analyzer(request)
    if analyzer is None:
        if record is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI is not configured")
        return _out(record, user.language, premium=True)
    use_case = AnalyzePhotosUseCase(repository, analyzer, model=getattr(analyzer, "model", ""))
    try:
        if record is None or record.photos_hash != photos_fingerprint(listing.images):
            if await take_ai_request(session, user.id, now.date(), DAILY_LIMIT) is None:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS, f"Daily AI limit reached ({DAILY_LIMIT})"
                )
            await session.commit()
        record = await use_case.report_for(listing)
        await session.commit()
    except PhotoAnalysisError as exc:
        if record is None:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Photo analysis unavailable"
            ) from exc
    finally:
        if getattr(request.app.state, "photo_analyzer", None) is None:
            close = getattr(analyzer, "close", None)
            if close is not None:
                await close()
    return _out(record, user.language, premium=True)
