"""Listing geocoding: when the address was looked up on the map (TASK-080).

Revision ID: listing_geocoded
Revises: ai_usage
Create Date: 2026-09-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_geocoded"
down_revision = "ai_usage"
branch_labels = None
depends_on = None

TABLE = "bina_listings"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("geocoded_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column(TABLE, "geocoded_at")
