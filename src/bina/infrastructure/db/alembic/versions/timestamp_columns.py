"""Add missing created_at/updated_at columns expected by the models.

Every model inherits both timestamps from ``Base``; ``bina_scrape_skips``,
``bina_ai_usage`` (TASK-095) and ``bina_complaints`` (TASK-106) were created
without some of them, so selecting whole rows failed.

Revision ID: timestamp_columns
Revises: premium_reminders
Create Date: 2026-09-30

"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "timestamp_columns"
down_revision = "premium_reminders"
branch_labels = None
depends_on = None


def _timestamp(name: str) -> sa.Column[Any]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.add_column("bina_scrape_skips", _timestamp("created_at"))
    op.add_column("bina_scrape_skips", _timestamp("updated_at"))
    op.add_column("bina_ai_usage", _timestamp("created_at"))
    op.add_column("bina_ai_usage", _timestamp("updated_at"))
    op.add_column("bina_complaints", _timestamp("updated_at"))


def downgrade() -> None:
    op.drop_column("bina_complaints", "updated_at")
    op.drop_column("bina_ai_usage", "updated_at")
    op.drop_column("bina_ai_usage", "created_at")
    op.drop_column("bina_scrape_skips", "updated_at")
    op.drop_column("bina_scrape_skips", "created_at")
