"""Проверка собственника по документу (TASK-098)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Verification(Base):
    """Заявка «я собственник»: документ в Telegram, решение администратора."""

    __tablename__ = "bina_verifications"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    listing_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # pending / approved / rejected (bina.application.verification.VerificationStatus)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending", index=True)
    # Документ хранится только в Telegram (file_id); после решения стирается
    file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # photo / document — как отправить документ администратору
    file_kind: Mapped[str] = mapped_column(String(10), nullable=False, default="photo")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
