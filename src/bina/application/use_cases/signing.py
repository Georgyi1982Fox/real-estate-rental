"""Подпись документов двумя сторонами (TASK-115)."""

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from bina.application.signing import (
    SIGNERS,
    DocumentKind,
    DocumentStatus,
    Signer,
    SignError,
    SignErrorCode,
    check_can_sign,
    fingerprint,
)
from bina.infrastructure.db.models import SignedDocument, User

# Сколько документов показывать в «Мои документы»
MY_DOCUMENTS = 20


class IDocuments(Protocol):
    async def create(self, document: SignedDocument) -> SignedDocument: ...

    async def get(self, document_id: UUID) -> SignedDocument | None: ...

    async def by_token(self, token: str) -> SignedDocument | None: ...

    async def signers(self, document_id: UUID) -> list[Signer]: ...

    async def add_signature(self, document_id: UUID, signer: Signer) -> None: ...

    async def set_status(
        self, document: SignedDocument, status: str, completed_at: datetime | None = None
    ) -> None: ...

    async def for_user(self, user_id: UUID, limit: int) -> list[SignedDocument]: ...


@dataclass(frozen=True, slots=True)
class SignResult:
    document: SignedDocument
    signers: list[Signer]

    @property
    def completed(self) -> bool:
        return self.document.status == DocumentStatus.SIGNED


class SigningUseCase:
    def __init__(self, documents: IDocuments) -> None:
        self._documents = documents

    async def create(
        self,
        creator: User,
        kind: DocumentKind,
        title: str,
        filename: str,
        content: bytes,
        listing_id: UUID | None,
    ) -> SignedDocument:
        return await self._documents.create(
            SignedDocument(
                kind=kind.value,
                title=title[:200],
                filename=filename[:120],
                content=content,
                sha256=fingerprint(content),
                creator_id=creator.id,
                listing_id=listing_id,
                token=secrets.token_urlsafe(16),
                status=DocumentStatus.PENDING.value,
            )
        )

    async def open(self, token: str) -> SignResult:
        document = await self._documents.by_token(token)
        if document is None:
            raise SignError(SignErrorCode.NOT_FOUND)
        return SignResult(document, await self._documents.signers(document.id))

    async def participant(self, document_id: UUID, user_id: UUID) -> SignResult:
        """Документ, в котором ``user_id`` — создатель или подписант; иначе NOT_FOUND."""
        document = await self._documents.get(document_id)
        if document is None:
            raise SignError(SignErrorCode.NOT_FOUND)
        signers = await self._documents.signers(document.id)
        if document.creator_id != user_id and all(s.user_id != user_id for s in signers):
            raise SignError(SignErrorCode.NOT_FOUND)
        return SignResult(document, signers)

    async def sign(self, document_id: UUID, user: User, name: str, now: datetime) -> SignResult:
        document = await self._documents.get(document_id)
        if document is None:
            raise SignError(SignErrorCode.NOT_FOUND)
        signers = await self._documents.signers(document.id)
        check_can_sign(document.status, document.creator_id, signers, user.id)
        signer = Signer(user.id, name.strip()[:130] or str(user.telegram_id), user.telegram_id, now)
        await self._documents.add_signature(document.id, signer)
        signers = [*signers, signer]
        if len(signers) >= SIGNERS:
            await self._documents.set_status(document, DocumentStatus.SIGNED.value, now)
        return SignResult(document, signers)

    async def decline(self, document_id: UUID, user: User) -> SignResult:
        """Отказ подписывать: создатель отменяет, вторая сторона отказывается."""
        document = await self._documents.get(document_id)
        if document is None:
            raise SignError(SignErrorCode.NOT_FOUND)
        if document.status != DocumentStatus.PENDING:
            raise SignError(SignErrorCode.CLOSED)
        signers = await self._documents.signers(document.id)
        if any(s.user_id == user.id for s in signers) and user.id != document.creator_id:
            raise SignError(SignErrorCode.ALREADY_SIGNED)
        await self._documents.set_status(document, DocumentStatus.DECLINED.value)
        return SignResult(document, signers)

    async def mine(self, user_id: UUID) -> list[SignedDocument]:
        return await self._documents.for_user(user_id, MY_DOCUMENTS)
