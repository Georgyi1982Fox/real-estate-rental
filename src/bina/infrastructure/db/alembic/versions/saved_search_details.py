"""All filters in a saved search: area, text, floor, amenities, condition, owner (TASK-086).

Revision ID: saved_search_details
Revises: listing_checked_at
Create Date: 2026-09-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "saved_search_details"
down_revision = "listing_checked_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bina_saved_searches",
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("bina_saved_searches", "details")
