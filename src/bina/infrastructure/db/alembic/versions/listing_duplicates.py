"""Listing duplicates: the same apartment on another site (TASK-090).

Revision ID: listing_duplicates
Revises: saved_search_details
Create Date: 2026-09-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "listing_duplicates"
down_revision = "saved_search_details"
branch_labels = None
depends_on = None

TABLE = "bina_listings"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "duplicate_of",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{TABLE}.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        TABLE, sa.Column("duplicates_checked_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_bina_listings_duplicate_of", TABLE, ["duplicate_of"])


def downgrade() -> None:
    op.drop_index("ix_bina_listings_duplicate_of", table_name=TABLE)
    op.drop_column(TABLE, "duplicates_checked_at")
    op.drop_column(TABLE, "duplicate_of")
