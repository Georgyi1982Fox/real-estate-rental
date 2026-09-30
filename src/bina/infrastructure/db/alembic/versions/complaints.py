"""Complaints about listings and hiding listings from search (TASK-106).

Revision ID: complaints
Revises: listing_geocoded
Create Date: 2026-09-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "complaints"
down_revision = "listing_geocoded"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bina_complaints",
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_listings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_bina_complaints_user_created", "bina_complaints", ["user_id", "created_at"])
    op.add_column(
        "bina_listings", sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("bina_listings", "hidden_at")
    op.drop_index("ix_bina_complaints_user_created", table_name="bina_complaints")
    op.drop_table("bina_complaints")
