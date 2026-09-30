"""Premium expiry reminders: which expiry date was already reminded (TASK-107).

Revision ID: premium_reminders
Revises: complaints
Create Date: 2026-09-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "premium_reminders"
down_revision = "complaints"
branch_labels = None
depends_on = None

TABLE = "bina_users"


def upgrade() -> None:
    op.add_column(
        TABLE, sa.Column("premium_reminded_for", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        TABLE, sa.Column("premium_expired_notified_for", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column(TABLE, "premium_expired_notified_for")
    op.drop_column(TABLE, "premium_reminded_for")
