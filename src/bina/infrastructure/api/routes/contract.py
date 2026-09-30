"""Двуязычный договор аренды в PDF — только Premium (TASK-101).

``POST /api/listings/{id}/contract``: пользователь заполняет анкету (имена сторон,
срок, залог…), остальное берётся из объявления. Договор — грузинский текст и
русский/английский параллельно.

- ``delivery=chat`` (по умолчанию) — бот присылает PDF в чат с пользователем:
  из Mini App так проще всего сохранить и переслать файл хозяину.
- ``delivery=file`` — PDF в ответе (для браузера и проверки).

Без Premium — 402.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal, Protocol

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from bina.application.contract import SECOND_LANGUAGES, ContractData, Utilities
from bina.application.subscriptions import is_premium
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
LANGUAGE_NAMES = {
    "ru": {"ru": "русский", "en": "английский"},
    "en": {"ru": "Russian", "en": "English"},
    "ka": {"ru": "რუსული", "en": "ინგლისური"},
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
    delivery: Literal["chat", "file"] = "chat"

    @field_validator("landlord_name", "tenant_name", "landlord_id", "tenant_id", "address", "notes")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean_text(value)


class ContractSentOut(BaseModel):
    """Договор отправлен в чат."""

    sent: bool
    filename: str


class DocumentSender(Protocol):
    """Отправка файла пользователю в Telegram (в тестах — подмена)."""

    async def __call__(self, chat_id: int, filename: str, content: bytes, caption: str) -> None: ...


@dataclass(frozen=True, slots=True)
class BotDocumentSender:
    """Отправка через Bot API ``sendDocument``."""

    bot_token: str

    async def __call__(self, chat_id: int, filename: str, content: bytes, caption: str) -> None:
        bot = Bot(token=self.bot_token)
        try:
            await bot.send_document(
                chat_id, BufferedInputFile(content, filename=filename), caption=caption
            )
        finally:
            await bot.session.close()


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


def _sender(request: Request, bot_token: str | None) -> DocumentSender:
    injected: DocumentSender | None = getattr(request.app.state, "document_sender", None)
    if injected is not None:
        return injected
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bot is not configured"
        )
    return BotDocumentSender(bot_token)


@router.post(
    "/{listing_id}/contract",
    response_model=ContractSentOut,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def make_contract(
    listing_id: str,
    body: ContractIn,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> ContractSentOut | Response:
    """Договор аренды в PDF (Premium): в чат с ботом или файлом в ответе."""
    if not is_premium(user, datetime.now(UTC)):
        raise payment_required("contract", 0)
    listing = await get_listing_or_404(session, listing_id)
    if not (body.address or listing.address):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="address is required"
        )
    second = body.second_language or (user.language if user.language in SECOND_LANGUAGES else "en")
    pdf = render_contract(contract_data(body, listing), second)
    filename = f"bina-contract-{body.start_date:%Y-%m-%d}.pdf"
    if body.delivery == "file":
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    language = user.language if user.language in CAPTIONS else "en"
    caption = CAPTIONS[language].format(lang=LANGUAGE_NAMES[language][second])
    try:
        await _sender(request, settings.bot_token)(user.telegram_id, filename, pdf, caption)
    except TelegramAPIError as exc:
        # Например, пользователь не запускал бота или заблокировал его
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not send the file to the chat"
        ) from exc
    return ContractSentOut(sent=True, filename=filename)
