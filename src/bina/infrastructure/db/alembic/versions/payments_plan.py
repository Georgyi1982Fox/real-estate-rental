"""Plan of a payment (TASK-026).

Revision ID: payments_plan
Revises: listing_search_vector
Create Date: 2026-09-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "payments_plan"
down_revision = "listing_search_vector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bina_payments", sa.Column("plan", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("bina_payments", "plan")
