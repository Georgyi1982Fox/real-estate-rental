"""Документы на подпись и подписи (TASK-115)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SignedDocument(Base):
    """Договор или акт: файл, его отпечаток и ссылка для второй стороны."""

    __tablename__ = "bina_documents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # contract / acceptance
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    filename: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    creator_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    listing_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bina_listings.id", ondelete="SET NULL"), nullable=True
    )
    # Ссылка для второй стороны: /start sign_<token>
    token: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    # pending / signed / declined (bina.application.signing.DocumentStatus)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentSignature(Base):
    """Подпись: кто (аккаунт Telegram) и когда согласился с документом."""

    __tablename__ = "bina_document_signatures"

    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(130), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
