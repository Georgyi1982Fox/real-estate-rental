"""AI photo reports (TASK-114).

Revision ID: photo_reports
Revises: promotion_verification
Create Date: 2026-10-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "photo_reports"
down_revision = "promotion_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bina_listings", sa.Column("repair_level", sa.String(16), nullable=True))
    op.create_table(
        "bina_photo_reports",
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_listings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("summary_ru", sa.Text(), nullable=False, server_default=""),
        sa.Column("summary_en", sa.Text(), nullable=False, server_default=""),
        sa.Column("summary_ka", sa.Text(), nullable=False, server_default=""),
        sa.Column("photos_hash", sa.String(40), nullable=False),
        sa.Column("model", sa.String(60), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("bina_photo_reports")
    op.drop_column("bina_listings", "repair_level")
