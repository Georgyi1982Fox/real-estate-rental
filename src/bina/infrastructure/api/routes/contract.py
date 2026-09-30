"""Двуязычный договор аренды в PDF — только Premium (TASK-101).

``POST /api/listings/{id}/contract``: пользователь заполняет анкету (имена сторон,
срок, залог…), остальное берётся из объявления. Договор — грузинский текст и
русский/английский параллельно.
PDF — в чат с ботом или файлом в ответе (``delivery``, см. ``api/delivery.py``).

Без Premium — 402.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from bina.application.contract import ContractData, Utilities
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
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.db.models import Listing
from bina.infrastructure.documents.contract_pdf import render_contract

router = APIRouter(prefix="/api/listings", tags=["documents"])

# Подпись к файлу в чате — на языке пользователя
CAPTIONS = {
    "ru": "Договор аренды (грузинский + {lang}). Проверьте данные перед подписанием.",
    "en": "Lease agreement (Georgian + {lang}). Check the details before signing.",
    "ka": "ქირავნობის ხელშეკრულება (ქართული + {lang}). ხელმოწერამდე შეამოწმეთ მონაცემები.",
}


class ContractIn(BaseModel):
    """Анкета договора. Пустые адрес, плата и валюта берутся из объявления."""

    second_language: Literal["ru", "en"] | None = Field(
        default=None, description="Второй язык договора; по умолчанию — язык пользователя"
    )
    landlord_name: str = Field(min_length=2, max_length=120)
    tenant_name: str = Field(min_length=2, max_length=120)
    landlord_id: str = Field(default="", max_length=40, description="Паспорт / ID")
    tenant_id: str = Field(default="", max_length=40, description="Паспорт / ID")
    address: str = Field(default="", max_length=200)
    start_date: date
    months: int = Field(ge=1, le=60)
    rent: Decimal | None = Field(default=None, gt=0, le=1_000_000)
    currency: Literal["GEL", "USD", "EUR"] | None = None
    deposit: Decimal = Field(default=Decimal(0), ge=0, le=1_000_000)
    payment_day: int = Field(default=1, ge=1, le=28)
    utilities: Utilities = Utilities.TENANT
    pets_allowed: bool = False
    notes: str = Field(default="", max_length=500)
    delivery: Delivery = "chat"

    @field_validator("landlord_name", "tenant_name", "landlord_id", "tenant_id", "address", "notes")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean_text(value)


def contract_data(body: ContractIn, listing: Listing) -> ContractData:
    """Данные договора: анкета + объявление."""
    return ContractData(
        landlord_name=body.landlord_name,
        tenant_name=body.tenant_name,
        landlord_id=body.landlord_id,
        tenant_id=body.tenant_id,
        address=body.address or listing.address or "",
        rooms=listing.rooms,
        area=float(listing.area),
        start=body.start_date,
        months=body.months,
        rent=body.rent if body.rent is not None else listing.price,
        currency=body.currency or listing.currency,
        deposit=body.deposit,
        payment_day=body.payment_day,
        utilities=body.utilities,
        pets_allowed=body.pets_allowed,
        notes=body.notes,
    )


@router.post(
    "/{listing_id}/contract",
    response_model=DocumentSentOut,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def make_contract(
    listing_id: str,
    body: ContractIn,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> DocumentSentOut | Response:
    """Договор аренды в PDF (Premium): в чат с ботом или файлом в ответе."""
    if not has_premium_access(user, datetime.now(UTC)):
        raise payment_required("contract", 0)
    listing = await get_listing_or_404(session, listing_id)
    if not (body.address or listing.address):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="address is required"
        )
    second = second_language(user, body.second_language)
    language = ui_language(user)
    return await deliver_pdf(
        request,
        settings,
        user,
        pdf=render_contract(contract_data(body, listing), second),
        filename=f"bina-contract-{body.start_date:%Y-%m-%d}.pdf",
        caption=CAPTIONS[language].format(lang=LANGUAGE_NAMES[language][second]),
        delivery=body.delivery,
    )
