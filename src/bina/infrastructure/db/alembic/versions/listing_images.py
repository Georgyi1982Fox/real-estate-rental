"""Add images column to listings.

Revision ID: listing_images
Revises: initial_db_structure
Create Date: 2026-09-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_images"
down_revision = "initial_db_structure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bina_listings",
        sa.Column("images", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("bina_listings", "images")
