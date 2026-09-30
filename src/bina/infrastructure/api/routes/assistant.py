"""AI-помощник арендатора — только Premium (TASK-095).

- ``POST /api/listings/{id}/assistant`` — ``message_owner`` (сообщение хозяину на
  грузинском с переводом) или ``viewing_questions`` (что спросить на просмотре).
- ``GET /api/listings/{id}/cheaper`` — похожие квартиры дешевле (без AI).

Без Premium — 402. Запросов к AI — не больше ``ASSISTANT_DAILY_LIMIT`` в день (429).
"""

import os
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from bina.application.ports.assistant import AssistantError, IAssistant, ListingBrief
from bina.application.subscriptions import has_premium_access
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import get_listing_or_404, payment_required
from bina.infrastructure.api.schemas import ListingOut, ListingsOut
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.db.models import Listing, User
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.users import take_ai_request
from bina.infrastructure.llm.assistant import LLMAssistant
from bina.infrastructure.llm.llm_factory import LLMFactory

router = APIRouter(prefix="/api/listings", tags=["assistant"])

# Запросов к AI-помощнику на пользователя в день (расход на AI)
DAILY_LIMIT = int(os.getenv("ASSISTANT_DAILY_LIMIT", "30"))
CHEAPER_LIMIT = 5


class AssistantIn(BaseModel):
    """Тело запроса к помощнику."""

    action: Literal["message_owner", "viewing_questions"]
    note: str = Field(
        default="",
        max_length=300,
        description="О себе, если нужно: «двое, с кошкой, с 1 ноября, на год»",
    )

    @field_validator("note")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean_text(value)


class AssistantOut(BaseModel):
    """Ответ помощника."""

    action: str
    # message_owner: сообщение на грузинском и перевод на язык пользователя
    text_ka: str | None = None
    translation: str | None = None
    # viewing_questions: вопросы на языке пользователя
    questions: list[str] = Field(default_factory=list)
    remaining_today: int


def listing_brief(listing: Listing, language: str) -> ListingBrief:
    """Объявление для AI на языке пользователя (что есть)."""
    title = getattr(listing, f"title_{language}", "") or listing.title_ru or listing.title_ka
    description = (
        getattr(listing, f"description_{language}", "")
        or listing.description_ru
        or listing.description_ka
        or ""
    )
    district = listing.district
    return ListingBrief(
        title=title or "",
        description=description,
        price=f"{listing.price:.0f} {listing.currency}",
        rooms=listing.rooms,
        area=float(listing.area),
        district=(district.name_en or district.name_ru or "") if district else "",
        floor=listing.floor,
        total_floors=listing.total_floors,
        address=listing.address,
        features=list(listing.features or []),
    )


def _require_premium(user: User) -> None:
    if not has_premium_access(user, datetime.now(UTC)):
        raise payment_required("assistant", 0)


def _assistant(request: Request) -> IAssistant:
    """Помощник: в тестах подменяется через ``app.state.assistant``."""
    injected: IAssistant | None = getattr(request.app.state, "assistant", None)
    if injected is not None:
        return injected
    if not os.getenv("LLM_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI is not configured"
        )
    return LLMAssistant(LLMFactory.create_provider())


@router.post("/{listing_id}/assistant", response_model=AssistantOut)
async def ask_assistant(
    listing_id: str, body: AssistantIn, request: Request, user: CurrentUserDep, session: SessionDep
) -> AssistantOut:
    """AI-помощник (Premium): сообщение хозяину или вопросы для просмотра."""
    _require_premium(user)
    listing = await get_listing_or_404(session, listing_id)
    # Район для текста AI (в асинхронном режиме связи не подгружаются сами)
    await session.refresh(listing, attribute_names=["district"])
    brief = listing_brief(listing, user.language)
    now = datetime.now(UTC)
    used = await take_ai_request(session, user.id, now.date(), DAILY_LIMIT)
    if used is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily assistant limit reached ({DAILY_LIMIT})",
        )
    # Счётчик сохраняем сразу: ответ AI долгий, а лимит должен работать и при ошибке
    await session.commit()
    assistant = _assistant(request)
    try:
        if body.action == "message_owner":
            message = await assistant.message_owner(brief, user.language, body.note)
            return AssistantOut(
                action=body.action,
                text_ka=message.text_ka,
                translation=message.translation,
                remaining_today=DAILY_LIMIT - used,
            )
        questions = await assistant.viewing_questions(brief, user.language, body.note)
        return AssistantOut(
            action=body.action, questions=questions, remaining_today=DAILY_LIMIT - used
        )
    except AssistantError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="AI did not answer, try again"
        ) from exc
    finally:
        if getattr(request.app.state, "assistant", None) is None:
            close = getattr(assistant, "close", None)
            if close is not None:
                await close()


@router.get("/{listing_id}/cheaper", response_model=ListingsOut)
async def cheaper_similar(
    listing_id: str, user: CurrentUserDep, session: SessionDep
) -> ListingsOut:
    """Похожие квартиры дешевле (Premium): тот же район и комнаты, площадь ±20%."""
    _require_premium(user)
    listing = await get_listing_or_404(session, listing_id)
    items = await ListingsRepository(session).cheaper_similar(listing, CHEAPER_LIMIT)
    return ListingsOut(items=[ListingOut.from_model(item) for item in items])
