"""City of a district: Tbilisi or Batumi (TASK-079).

Revision ID: district_city
Revises: rent_reminders
Create Date: 2026-09-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "district_city"
down_revision = "rent_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Все районы до TASK-079 — тбилисские
    op.add_column(
        "bina_districts",
        sa.Column("city", sa.String(20), nullable=False, server_default="tbilisi"),
    )
    op.create_index("ix_bina_districts_city", "bina_districts", ["city"])


def downgrade() -> None:
    op.drop_index("ix_bina_districts_city", table_name="bina_districts")
    op.drop_column("bina_districts", "city")
