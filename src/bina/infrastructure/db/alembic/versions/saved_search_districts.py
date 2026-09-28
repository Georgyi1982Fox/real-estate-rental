"""Several districts in a saved search.

Revision ID: saved_search_districts
Revises: listing_fraud
Create Date: 2026-09-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "saved_search_districts"
down_revision = "listing_fraud"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Два и больше районов; один район по-прежнему в district_id
    op.add_column(
        "bina_saved_searches",
        sa.Column("district_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bina_saved_searches", "district_ids")
