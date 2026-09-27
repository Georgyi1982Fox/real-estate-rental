"""Add source url, phone and owner name to listings.

Revision ID: listing_contacts
Revises: listing_images
Create Date: 2026-09-27

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_contacts"
down_revision = "listing_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bina_listings", sa.Column("url", sa.String(), nullable=True))
    op.add_column("bina_listings", sa.Column("phone", sa.String(), nullable=True))
    op.add_column("bina_listings", sa.Column("owner_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("bina_listings", "owner_name")
    op.drop_column("bina_listings", "phone")
    op.drop_column("bina_listings", "url")
