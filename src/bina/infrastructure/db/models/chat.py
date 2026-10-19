"""Чат арендатора с хозяином и просмотры (TASK-111, TASK-112)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _user_fk() -> Mapped[UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def _listing_fk() -> Mapped[UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class Conversation(Base):
    """Диалог с хозяином об одной квартире или гостинице (TASK-120).

    Один на пару «квартира — арендатор» или «гостиница — гость»; ``tenant_id`` — тот,
    кто написал первым, ``owner_id`` — хозяин.
    """

    __tablename__ = "bina_conversations"
    __table_args__ = (
        UniqueConstraint("listing_id", "tenant_id", name="uq_bina_conversations"),
        UniqueConstraint("hotel_id", "tenant_id", name="uq_bina_conversations_hotel"),
        CheckConstraint(
            "(listing_id IS NULL) <> (hotel_id IS NULL)", name="ck_bina_conversations_subject"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    listing_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_listings.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    hotel_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_hotels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    tenant_id: Mapped[UUID] = _user_fk()
    owner_id: Mapped[UUID] = _user_fk()


class ChatMessage(Base):
    """Сообщение диалога: как написано и как доставлено (перевод) — контекст беседы."""

    __tablename__ = "bina_chat_messages"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[UUID] = _user_fk()
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Перевод на язык получателя; None — тот же язык или перевод не удался
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_language: Mapped[str] = mapped_column(String(2), nullable=False)


class Viewing(Base):
    """Просьба о просмотре: время по выбору арендатора, ответ хозяина."""

    __tablename__ = "bina_viewings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    listing_id: Mapped[UUID] = _listing_fk()
    tenant_id: Mapped[UUID] = _user_fk()
    owner_id: Mapped[UUID] = _user_fk()
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # bina.application.chat.ViewingStatus
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending", index=True)
    # Когда напомнили о подтверждённом просмотре (за 2 часа)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
