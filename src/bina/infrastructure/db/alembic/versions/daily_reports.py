"""Daily owner report: which days were already sent (TASK-041).

Revision ID: daily_reports
Revises: agencies
Create Date: 2026-10-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "daily_reports"
down_revision = "agencies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bina_daily_reports",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("bina_daily_reports")
