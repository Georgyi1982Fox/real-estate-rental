"""Paid promotion and owner verification (TASK-097, TASK-098).

Revision ID: promotion_verification
Revises: chat_viewings
Create Date: 2026-10-02

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "promotion_verification"
down_revision = "chat_viewings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bina_listings", sa.Column("promoted_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "bina_listings", sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_bina_listings_promoted_until", "bina_listings", ["promoted_until"])
    op.create_table(
        "bina_verifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("file_id", sa.String(), nullable=True),
        sa.Column("file_kind", sa.String(10), nullable=False, server_default="photo"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for column in ("listing_id", "user_id", "status"):
        op.create_index(f"ix_bina_verifications_{column}", "bina_verifications", [column])


def downgrade() -> None:
    for column in ("listing_id", "user_id", "status"):
        op.drop_index(f"ix_bina_verifications_{column}", table_name="bina_verifications")
    op.drop_table("bina_verifications")
    op.drop_index("ix_bina_listings_promoted_until", table_name="bina_listings")
    op.drop_column("bina_listings", "promoted_at")
    op.drop_column("bina_listings", "promoted_until")
