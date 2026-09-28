"""Add English title and description to listings (AI translation, TASK-010).

Revision ID: listing_translations_en
Revises: listing_contacts
Create Date: 2026-09-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_translations_en"
down_revision = "listing_contacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bina_listings",
        sa.Column("title_en", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "bina_listings",
        sa.Column("description_en", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("bina_listings", "description_en")
    op.drop_column("bina_listings", "title_en")
