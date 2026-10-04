"""Акт приёма-передачи квартиры (TASK-102).

- ``GET /api/documents/acceptance/checklist`` — чек-лист на языке пользователя
  (разделы, пункты, состояния), чтобы Mini App не хранил тексты у себя.
- ``POST /api/documents/acceptance`` — PDF акта (Premium): грузинский и русский/английский.
  ``listing_id`` необязателен: адрес подставляется из объявления.

PDF — в чат с ботом или файлом в ответе (``delivery``, см. ``api/delivery.py``).
"""

from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from bina.application.acceptance import (
    CHECKLIST,
    ITEMS,
    STATUS_LABELS,
    AcceptanceData,
    CheckedItem,
    ItemStatus,
)
from bina.application.cities import city
from bina.application.signing import DocumentKind
from bina.application.subscriptions import has_premium_access
from bina.infrastructure.api.delivery import (
    LANGUAGE_NAMES,
    Delivery,
    DocumentSentOut,
    deliver_pdf,
    second_language,
    ui_language,
)
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep, SettingsDep
from bina.infrastructure.api.routes.common import get_listing_or_404, payment_required
from bina.infrastructure.api.routes.documents import SigningStartedOut, start_signing
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.documents.acceptance_pdf import render_acceptance

router = APIRouter(prefix="/api/documents", tags=["documents"])

CAPTIONS = {
    "ru": "Акт приёмки квартиры (грузинский + {lang}). Подпишите его вместе с хозяином.",
    "en": "Apartment handover report (Georgian + {lang}). Sign it together with the landlord.",
    "ka": "ბინის მიღება-ჩაბარების აქტი (ქართული + {lang}). ხელი მოაწერეთ გამქირავებელთან ერთად.",
}


class ChecklistItemOut(BaseModel):
    code: str
    title: str


class ChecklistSectionOut(BaseModel):
    code: str
    title: str
    items: list[ChecklistItemOut]


class StatusOut(BaseModel):
    code: str
    title: str


class ChecklistOut(BaseModel):
    """Чек-лист приёмки на языке пользователя."""

    sections: list[ChecklistSectionOut]
    statuses: list[StatusOut]


class CheckedItemIn(BaseModel):
    code: str
    status: ItemStatus
    comment: str = Field(default="", max_length=200)

    @field_validator("code")
    @classmethod
    def _known(cls, value: str) -> str:
        if value not in ITEMS:
            raise ValueError(f"unknown checklist item: {value}")
        return value

    @field_validator("comment")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean_text(value)


class AcceptanceIn(BaseModel):
    """Данные акта. Пункты, которых нет в запросе, в акт не попадают."""

    listing_id: str | None = None
    second_language: Literal["ru", "en"] | None = None
    landlord_name: str = Field(min_length=2, max_length=120)
    tenant_name: str = Field(min_length=2, max_length=120)
    address: str = Field(default="", max_length=200)
    handover_date: date | None = Field(default=None, description="По умолчанию — сегодня")
    items: list[CheckedItemIn] = Field(min_length=1, max_length=len(ITEMS))
    keys: int | None = Field(default=None, ge=0, le=50)
    electricity: str = Field(default="", max_length=20)
    gas: str = Field(default="", max_length=20)
    water: str = Field(default="", max_length=20)
    notes: str = Field(default="", max_length=500)
    delivery: Delivery = "chat"

    @field_validator(
        "landlord_name", "tenant_name", "address", "electricity", "gas", "water", "notes"
    )
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean_text(value)

    @field_validator("items")
    @classmethod
    def _unique(cls, items: list[CheckedItemIn]) -> list[CheckedItemIn]:
        codes = [item.code for item in items]
        if len(set(codes)) != len(codes):
            raise ValueError("checklist items must not repeat")
        return items


@router.get("/acceptance/checklist", response_model=ChecklistOut)
async def acceptance_checklist(user: CurrentUserDep) -> ChecklistOut:
    """Разделы и пункты чек-листа, состояния — на языке пользователя."""
    language = ui_language(user)
    return ChecklistOut(
        sections=[
            ChecklistSectionOut(
                code=section.code,
                title=section.labels[language],
                items=[
                    ChecklistItemOut(code=item.code, title=item.labels[language])
                    for item in section.items
                ],
            )
            for section in CHECKLIST
        ],
        statuses=[
            StatusOut(code=code.value, title=labels[language])
            for code, labels in STATUS_LABELS.items()
        ],
    )


ACCEPTANCE_TITLES = {"ru": "Акт приёмки", "en": "Handover report", "ka": "მიღება-ჩაბარების აქტი"}


@router.post(
    "/acceptance",
    response_model=DocumentSentOut | SigningStartedOut,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def make_acceptance(
    body: AcceptanceIn,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> DocumentSentOut | SigningStartedOut | Response:
    """Акт приёмки в PDF (Premium): в чат, файлом или на подпись (``delivery=sign``)."""
    if not has_premium_access(user, datetime.now(UTC)):
        raise payment_required("acceptance", 0)
    address = body.address
    city_code = "tbilisi"
    listing_id = None
    if body.listing_id:
        listing = await get_listing_or_404(session, body.listing_id)
        listing_id = listing.id
        await session.refresh(listing, attribute_names=["district"])
        city_code = listing.district.city if listing.district else city_code
        address = address or listing.address or ""
    if not address:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="address is required"
        )
    handover = body.handover_date or datetime.now(UTC).date()
    data = AcceptanceData(
        landlord_name=body.landlord_name,
        tenant_name=body.tenant_name,
        address=address,
        handover_date=handover,
        city=city(city_code).names["en"],
        items=tuple(CheckedItem(item.code, item.status, item.comment) for item in body.items),
        keys=body.keys,
        electricity=body.electricity,
        gas=body.gas,
        water=body.water,
        notes=body.notes,
    )
    second = second_language(user, body.second_language)
    language = ui_language(user)
    pdf = render_acceptance(data, second, today=handover)
    filename = f"bina-acceptance-{handover:%Y-%m-%d}.pdf"
    if body.delivery == "sign":
        # TASK-115: сохранить и отправить на подпись обеим сторонам
        return await start_signing(
            request,
            settings,
            session,
            user,
            kind=DocumentKind.ACCEPTANCE,
            title=f"{ACCEPTANCE_TITLES[language]}: {address}",
            filename=filename,
            pdf=pdf,
            listing_id=listing_id,
        )
    return await deliver_pdf(
        request,
        settings,
        user,
        pdf=pdf,
        filename=filename,
        caption=CAPTIONS[language].format(lang=LANGUAGE_NAMES[language][second]),
        delivery=body.delivery,
    )
