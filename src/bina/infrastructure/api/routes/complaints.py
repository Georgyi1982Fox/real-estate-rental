"""Жалобы на объявления (TASK-106).

- ``GET /api/complaints/reasons`` — причины на языке пользователя.
- ``POST /api/listings/{id}/complaints`` — пожаловаться (одна жалоба от человека
  на объявление, повторная обновляет причину). От 3 разных людей — объявление
  скрывается из поиска до решения модератора.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from bina.application.complaints import DAILY_LIMIT, REASONS, Reason
from bina.infrastructure.api.delivery import ui_language
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import get_listing_or_404
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.db.repositories.complaints import ComplaintsRepository

router = APIRouter(tags=["complaints"])

THANKS = {
    "ka": "მადლობა! ჩვენ შევამოწმებთ განცხადებას.",
    "ru": "Спасибо! Мы проверим объявление.",
    "en": "Thank you! We will check the listing.",
}


class ReasonOut(BaseModel):
    code: str
    title: str


class ComplaintIn(BaseModel):
    reason: Reason
    comment: str = Field(default="", max_length=500)

    @field_validator("comment")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean_text(value)


class ComplaintOut(BaseModel):
    accepted: bool
    message: str


@router.get("/api/complaints/reasons", response_model=list[ReasonOut])
async def complaint_reasons(user: CurrentUserDep) -> list[ReasonOut]:
    """Причины жалобы по порядку показа."""
    language = ui_language(user)
    return [ReasonOut(code=code.value, title=labels[language]) for code, labels in REASONS.items()]


@router.post("/api/listings/{listing_id}/complaints", response_model=ComplaintOut)
async def complain(
    listing_id: str, body: ComplaintIn, user: CurrentUserDep, session: SessionDep
) -> ComplaintOut:
    """Пожаловаться на объявление."""
    listing = await get_listing_or_404(session, listing_id)
    repository = ComplaintsRepository(session)
    if await repository.count_today(user.id, datetime.now(UTC)) >= DAILY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily complaint limit reached ({DAILY_LIMIT})",
        )
    await repository.add(listing.id, user.id, body.reason.value, body.comment)
    await session.commit()
    # Скрыто ли объявление, пользователю не сообщаем: иначе проще проверять накрутку
    return ComplaintOut(accepted=True, message=THANKS[ui_language(user)])
