"""Документы на подпись (TASK-115)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.signing import Signer
from bina.infrastructure.db.models import DocumentSignature, SignedDocument


class DocumentsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: SignedDocument) -> SignedDocument:
        self._session.add(document)
        await self._session.flush()
        return document

    async def get(self, document_id: UUID) -> SignedDocument | None:
        return await self._session.get(SignedDocument, document_id)

    async def by_token(self, token: str) -> SignedDocument | None:
        query = select(SignedDocument).where(SignedDocument.token == token)
        return (await self._session.execute(query)).scalar_one_or_none()

    async def signers(self, document_id: UUID) -> list[Signer]:
        query = (
            select(DocumentSignature)
            .where(DocumentSignature.document_id == document_id)
            .order_by(DocumentSignature.signed_at)
        )
        return [
            Signer(row.user_id, row.name, row.telegram_id, row.signed_at)
            for row in (await self._session.execute(query)).scalars()
        ]

    async def add_signature(self, document_id: UUID, signer: Signer) -> None:
        self._session.add(
            DocumentSignature(
                document_id=document_id,
                user_id=signer.user_id,
                name=signer.name,
                telegram_id=signer.telegram_id,
                signed_at=signer.signed_at,
            )
        )
        await self._session.flush()

    async def set_status(
        self, document: SignedDocument, status: str, completed_at: datetime | None = None
    ) -> None:
        document.status = status
        document.completed_at = completed_at
        await self._session.flush()

    async def for_user(self, user_id: UUID, limit: int) -> list[SignedDocument]:
        """Свои документы: созданные или подписанные, новые сверху."""
        signed = select(DocumentSignature.document_id).where(DocumentSignature.user_id == user_id)
        query = (
            select(SignedDocument)
            .where(or_(SignedDocument.creator_id == user_id, SignedDocument.id.in_(signed)))
            .order_by(SignedDocument.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(query)).scalars().all())
