"""Rent payment reminders (TASK-109).

Revision ID: rent_reminders
Revises: referrals
Create Date: 2026-09-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "rent_reminders"
down_revision = "referrals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bina_rent_reminders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GEL"),
        sa.Column("paid_for", sa.Date(), nullable=True),
        sa.Column("last_reminded_on", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("day BETWEEN 1 AND 28", name="ck_bina_rent_reminders_day"),
    )
    op.create_index("ix_bina_rent_reminders_user_id", "bina_rent_reminders", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_bina_rent_reminders_user_id", table_name="bina_rent_reminders")
    op.drop_table("bina_rent_reminders")
