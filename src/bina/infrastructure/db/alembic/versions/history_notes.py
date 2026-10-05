"""View history and notes on favorites (TASK-074, TASK-075).

Revision ID: history_notes
Revises: documents
Create Date: 2026-10-05

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "history_notes"
down_revision = "documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bina_favorites", sa.Column("note", sa.Text(), nullable=False, server_default=""))
    op.create_table(
        "bina_view_history",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_listings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_bina_view_history_user_viewed", "bina_view_history", ["user_id", "viewed_at"]
    )


def downgrade() -> None:
    op.drop_table("bina_view_history")
    op.drop_column("bina_favorites", "note")
