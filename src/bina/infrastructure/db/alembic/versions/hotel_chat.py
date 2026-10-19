"""Chat with the hotel owner (TASK-120, stage 2).

A conversation is about an apartment (``listing_id``) or a hotel (``hotel_id``) — exactly one.

Revision ID: hotel_chat
Revises: hotels
Create Date: 2026-10-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "hotel_chat"
down_revision = "hotels"
branch_labels = None
depends_on = None

TABLE = "bina_conversations"


def upgrade() -> None:
    op.alter_column(TABLE, "listing_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.add_column(
        TABLE,
        sa.Column(
            "hotel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_hotels.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(f"ix_{TABLE}_hotel_id", TABLE, ["hotel_id"])
    op.create_unique_constraint("uq_bina_conversations_hotel", TABLE, ["hotel_id", "tenant_id"])
    op.create_check_constraint(
        "ck_bina_conversations_subject", TABLE, "(listing_id IS NULL) <> (hotel_id IS NULL)"
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM {TABLE} WHERE hotel_id IS NOT NULL")
    op.drop_constraint("ck_bina_conversations_subject", TABLE, type_="check")
    op.drop_constraint("uq_bina_conversations_hotel", TABLE, type_="unique")
    op.drop_index(f"ix_{TABLE}_hotel_id", table_name=TABLE)
    op.drop_column(TABLE, "hotel_id")
    op.alter_column(
        TABLE, "listing_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False
    )
