"""Skipped source items (Telegram posts that are not rentals), TASK-091.

Revision ID: scrape_skips
Revises: listing_duplicates
Create Date: 2026-09-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "scrape_skips"
down_revision = "listing_duplicates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bina_scrape_skips",
        sa.Column("source_name", sa.String(20), primary_key=True),
        sa.Column("source_id", sa.String(), primary_key=True),
        sa.Column(
            "skipped_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("bina_scrape_skips")
