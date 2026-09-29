"""Daily AI assistant usage per user (TASK-095).

Revision ID: ai_usage
Revises: scrape_skips
Create Date: 2026-09-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ai_usage"
down_revision = "scrape_skips"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bina_ai_usage",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("bina_ai_usage")
