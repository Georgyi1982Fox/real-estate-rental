"""Listing rent period: monthly or daily (TASK-092).

Revision ID: listing_rent_period
Revises: embeddings_unique
Create Date: 2026-09-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_rent_period"
down_revision = "embeddings_unique"
branch_labels = None
depends_on = None

TABLE = "bina_listings"


def upgrade() -> None:
    # Всё, что собрано до TASK-092, — помесячная аренда
    op.add_column(
        TABLE,
        sa.Column("rent_period", sa.String(10), nullable=False, server_default="monthly"),
    )
    op.create_index("ix_bina_listings_rent_period", TABLE, ["rent_period"])


def downgrade() -> None:
    op.drop_index("ix_bina_listings_rent_period", table_name=TABLE)
    op.drop_column(TABLE, "rent_period")
