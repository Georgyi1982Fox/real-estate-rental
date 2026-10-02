"""Chat with the landlord and viewings (TASK-111, TASK-112).

Revision ID: chat_viewings
Revises: listing_generated_titles
Create Date: 2026-10-02

"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "chat_viewings"
down_revision = "listing_generated_titles"
branch_labels = None
depends_on = None


def _id() -> sa.Column[Any]:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _fk(name: str, table: str) -> sa.Column[Any]:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey(f"{table}.id", ondelete="CASCADE"),
        nullable=False,
    )


def _timestamps() -> list[sa.Column[Any]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


INDEXES = {
    "bina_conversations": ("listing_id", "tenant_id", "owner_id"),
    "bina_chat_messages": ("conversation_id", "sender_id"),
    "bina_viewings": ("listing_id", "tenant_id", "owner_id", "status"),
}


def upgrade() -> None:
    op.create_table(
        "bina_conversations",
        _id(),
        _fk("listing_id", "bina_listings"),
        _fk("tenant_id", "bina_users"),
        _fk("owner_id", "bina_users"),
        *_timestamps(),
        sa.UniqueConstraint("listing_id", "tenant_id", name="uq_bina_conversations"),
    )
    op.create_table(
        "bina_chat_messages",
        _id(),
        _fk("conversation_id", "bina_conversations"),
        _fk("sender_id", "bina_users"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=True),
        sa.Column("target_language", sa.String(2), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "bina_viewings",
        _id(),
        _fk("listing_id", "bina_listings"),
        _fk("tenant_id", "bina_users"),
        _fk("owner_id", "bina_users"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("reminded_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    for table, columns in INDEXES.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table, columns in INDEXES.items():
        for column in columns:
            op.drop_index(f"ix_{table}_{column}", table_name=table)
    op.drop_table("bina_viewings")
    op.drop_table("bina_chat_messages")
    op.drop_table("bina_conversations")
