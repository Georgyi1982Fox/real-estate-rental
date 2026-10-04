"""Документы на подпись для Mini App (TASK-115).

- Договор или акт с ``delivery=sign`` — документ сохраняется, бот присылает его в чат, в
  ответе ссылка для второй стороны (``start_signing``).
- ``GET /api/documents`` — «Мои документы»: статус и кто подписал.
- ``GET /api/documents/{id}/file?part=document|certificate&delivery=chat|file`` — файл ещё раз.

Подписывают в боте: кнопка «Подписать» у документа (сторона подтверждает согласие своим
аккаунтом Telegram).
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.signing import DocumentKind, DocumentStatus, SignError, sign_link
from bina.application.use_cases.signing import SigningUseCase, SignResult
from bina.infrastructure.api.delivery import Delivery, DocumentSentOut, deliver_pdf, ui_language
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep, SettingsDep
from bina.infrastructure.api.routes.common import not_found
from bina.infrastructure.api.routes.referral import bot_username_or_none
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import User
from bina.infrastructure.db.repositories.documents import DocumentsRepository
from bina.infrastructure.documents.signature_certificate import render_certificate

router = APIRouter(prefix="/api/documents", tags=["documents"])

SIGN_CAPTIONS = {
    "ru": "Документ на подпись. Откройте ссылку, подпишите и перешлите её второй стороне:\n{link}",
    "en": "Document for signing. Open the link, sign and forward it to the other party:\n{link}",
    "ka": (
        "ხელმოსაწერი დოკუმენტი. გახსენით ბმული, მოაწერეთ ხელი და გაუგზავნეთ მეორე მხარეს:\n{link}"
    ),
}


class SigningStartedOut(BaseModel):
    document_id: UUID
    invite_url: str = Field(description="Ссылка на бота: открыть документ и подписать")
    sent: bool = Field(description="Документ отправлен в чат с ботом")


class SignerOut(BaseModel):
    name: str
    signed_at: datetime
    me: bool


class DocumentOut(BaseModel):
    id: UUID
    kind: str
    title: str
    status: Literal["pending", "signed", "declined"]
    created_at: datetime
    completed_at: datetime | None
    sha256: str
    signers: list[SignerOut]
    invite_url: str | None = Field(
        default=None, description="Только создателю, пока документ ждёт подписей"
    )


class DocumentsOut(BaseModel):
    items: list[DocumentOut]


def _use_case(session: AsyncSession) -> SigningUseCase:
    return SigningUseCase(DocumentsRepository(session))


async def start_signing(
    request: Request,
    settings: ApiSettings,
    session: AsyncSession,
    user: User,
    *,
    kind: DocumentKind,
    title: str,
    filename: str,
    pdf: bytes,
    listing_id: UUID | None,
) -> SigningStartedOut:
    """Сохранить документ на подпись и прислать его создателю в чат со ссылкой."""
    username = await bot_username_or_none(request, settings)
    if not username:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Bot is not configured")
    document = await _use_case(session).create(user, kind, title, filename, pdf, listing_id)
    await session.commit()
    link = sign_link(username, document.token)
    caption = SIGN_CAPTIONS[ui_language(user)].format(link=link)
    sent = await deliver_pdf(
        request, settings, user, pdf=pdf, filename=filename, caption=caption, delivery="chat"
    )
    return SigningStartedOut(
        document_id=document.id,
        invite_url=link,
        sent=isinstance(sent, DocumentSentOut) and sent.sent,
    )


def _out(result: SignResult, user: User, username: str | None) -> DocumentOut:
    document = result.document
    invite = None
    if username and document.creator_id == user.id and document.status == DocumentStatus.PENDING:
        invite = sign_link(username, document.token)
    return DocumentOut(
        id=document.id,
        kind=document.kind,
        title=document.title,
        status=DocumentStatus(document.status).value,
        created_at=document.created_at,
        completed_at=document.completed_at,
        sha256=document.sha256,
        signers=[
            SignerOut(name=s.name, signed_at=s.signed_at, me=s.user_id == user.id)
            for s in result.signers
        ],
        invite_url=invite,
    )


@router.get("", response_model=DocumentsOut)
async def my_documents(
    request: Request, user: CurrentUserDep, session: SessionDep, settings: SettingsDep
) -> DocumentsOut:
    """Свои документы (созданные или подписанные), новые сверху."""
    use_case = _use_case(session)
    username = getattr(request.app.state, "bot_username", None) or (
        await bot_username_or_none(request, settings)
    )
    items = []
    for document in await use_case.mine(user.id):
        result = await use_case.participant(document.id, user.id)
        items.append(_out(result, user, username))
    return DocumentsOut(items=items)


@router.get(
    "/{document_id}/file",
    response_model=DocumentSentOut,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def document_file(
    document_id: UUID,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
    part: Annotated[Literal["document", "certificate"], Query()] = "document",
    delivery: Annotated[Delivery, Query()] = "chat",
) -> DocumentSentOut | Response:
    """Документ или сертификат подписи ещё раз: в чат с ботом или файлом."""
    try:
        result = await _use_case(session).participant(document_id, user.id)
    except SignError as exc:
        raise not_found("Document not found") from exc
    document = result.document
    if part == "certificate":
        if not result.completed:
            raise HTTPException(status.HTTP_409_CONFLICT, "Not signed by both parties yet")
        pdf = render_certificate(
            document.title,
            document.filename,
            document.sha256,
            document.created_at,
            document.completed_at,
            result.signers,
            ui_language(user),
        )
        filename = f"certificate-{document.filename}"
    else:
        pdf, filename = document.content, document.filename
    return await deliver_pdf(
        request,
        settings,
        user,
        pdf=pdf,
        filename=filename,
        caption=document.title,
        delivery="file" if delivery == "file" else "chat",
    )
