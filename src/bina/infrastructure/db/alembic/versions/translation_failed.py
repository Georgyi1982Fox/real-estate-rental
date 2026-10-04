"""Listings whose translation failed are retried after a day (translation fix).

Revision ID: translation_failed
Revises: daily_reports
Create Date: 2026-10-04

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "translation_failed"
down_revision = "daily_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bina_listings",
        sa.Column("translation_failed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bina_listings", "translation_failed_at")
