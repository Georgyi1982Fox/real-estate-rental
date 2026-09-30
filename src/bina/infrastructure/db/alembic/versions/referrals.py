"""Referral program: invite codes, who invited whom, rewards (TASK-108).

Revision ID: referrals
Revises: timestamp_columns
Create Date: 2026-09-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "referrals"
down_revision = "timestamp_columns"
branch_labels = None
depends_on = None

TABLE = "bina_users"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("referral_code", sa.String(16), nullable=True))
    op.create_unique_constraint("uq_bina_users_referral_code", TABLE, ["referral_code"])
    op.add_column(
        TABLE,
        sa.Column(
            "referred_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{TABLE}.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_bina_users_referred_by", TABLE, ["referred_by"])
    op.add_column(
        TABLE, sa.Column("referral_rewarded_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column(TABLE, "referral_rewarded_at")
    op.drop_index("ix_bina_users_referred_by", table_name=TABLE)
    op.drop_column(TABLE, "referred_by")
    op.drop_constraint("uq_bina_users_referral_code", TABLE, type_="unique")
    op.drop_column(TABLE, "referral_code")
