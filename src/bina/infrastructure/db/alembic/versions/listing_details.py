"""Listing details from the source page: floors, amenities, condition, dates (TASK-018).

Revision ID: listing_details
Revises: saved_search_districts
Create Date: 2026-09-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_details"
down_revision = "saved_search_districts"
branch_labels = None
depends_on = None

TABLE = "bina_listings"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("floor", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("total_floors", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("bedrooms", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("bathrooms", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("condition", sa.String(), nullable=True))
    op.add_column(
        TABLE, sa.Column("features", sa.JSON(), server_default=sa.text("'[]'"), nullable=False)
    )
    op.add_column(TABLE, sa.Column("owner_type", sa.String(), nullable=True))
    op.add_column(TABLE, sa.Column("address", sa.String(), nullable=True))
    op.add_column(TABLE, sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column(TABLE, sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column(
        TABLE, sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(TABLE, sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(TABLE, sa.Column("details_fetched_at", sa.DateTime(timezone=True), nullable=True))
    # «Новые сверху»: дата на сайте, для старых записей — дата появления у нас
    op.execute(
        f"CREATE INDEX ix_bina_listings_fresh ON {TABLE} "
        "((coalesce(source_updated_at, created_at)) DESC)"
    )


def downgrade() -> None:
    op.drop_index("ix_bina_listings_fresh", table_name=TABLE)
    for column in (
        "details_fetched_at",
        "source_updated_at",
        "source_published_at",
        "longitude",
        "latitude",
        "address",
        "owner_type",
        "features",
        "condition",
        "bathrooms",
        "bedrooms",
        "total_floors",
        "floor",
    ):
        op.drop_column(TABLE, column)
