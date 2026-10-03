"""Agencies, listing stats and daily bumps (TASK-100).

Revision ID: agencies
Revises: photo_reports
Create Date: 2026-10-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "agencies"
down_revision = "photo_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bina_agencies",
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
            unique=True,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("plan", sa.String(20), nullable=True),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "bina_listing_stats",
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_listings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contacts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.add_column(
        "bina_listings", sa.Column("bump_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "bina_listings", sa.Column("bumped_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("bina_listings", "bumped_at")
    op.drop_column("bina_listings", "bump_until")
    op.drop_table("bina_listing_stats")
    op.drop_table("bina_agencies")
