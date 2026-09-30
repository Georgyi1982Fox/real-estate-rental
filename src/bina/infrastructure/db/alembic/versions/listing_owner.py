"""Listings posted by owners themselves (TASK-096).

Revision ID: listing_owner
Revises: listing_rent_period
Create Date: 2026-09-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "listing_owner"
down_revision = "listing_rent_period"
branch_labels = None
depends_on = None

TABLE = "bina_listings"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_bina_listings_owner_user_id", TABLE, ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_bina_listings_owner_user_id", table_name=TABLE)
    op.drop_column(TABLE, "owner_user_id")
