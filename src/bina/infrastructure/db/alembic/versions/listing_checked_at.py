"""Listing checked_at: when the listing was last seen on the source site.

По ней парсер заново проверяет давно не виденные объявления и убирает снятые
с сайта в архив.

Revision ID: listing_checked_at
Revises: clean_html_texts
Create Date: 2026-09-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_checked_at"
down_revision = "clean_html_texts"
branch_labels = None
depends_on = None

TABLE = "bina_listings"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True))
    # Очередь проверки: активные, давно не виденные первыми
    op.execute(
        f"CREATE INDEX ix_bina_listings_checked ON {TABLE} (checked_at NULLS FIRST) "
        "WHERE status = 'active'"
    )


def downgrade() -> None:
    op.drop_index("ix_bina_listings_checked", table_name=TABLE)
    op.drop_column(TABLE, "checked_at")
