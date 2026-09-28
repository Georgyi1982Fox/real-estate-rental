"""Fraud check results on listings (TASK-011).

Revision ID: listing_fraud
Revises: payments_plan
Create Date: 2026-09-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_fraud"
down_revision = "payments_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bina_listings",
        sa.Column("fraud_reasons", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
    )
    op.add_column(
        "bina_listings",
        sa.Column("fraud_checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Выборка непроверенных: WHERE fraud_checked_at IS NULL
    op.create_index(
        "ix_bina_listings_fraud_unchecked",
        "bina_listings",
        ["created_at"],
        postgresql_where=sa.text("fraud_checked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_bina_listings_fraud_unchecked", table_name="bina_listings")
    op.drop_column("bina_listings", "fraud_checked_at")
    op.drop_column("bina_listings", "fraud_reasons")
