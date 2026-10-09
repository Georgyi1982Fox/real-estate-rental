"""Hotels section (TASK-120): hotels, room types and complaints.

Revision ID: hotels
Revises: retry_translations
Create Date: 2026-10-09

"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "hotels"
down_revision = "retry_translations"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column[datetime]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "bina_hotels",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("city", sa.String(30), nullable=False),
        sa.Column("address", sa.String(200), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("stars", sa.Integer(), nullable=True),
        sa.Column("amenities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("check_in", sa.String(5), nullable=True),
        sa.Column("check_out", sa.String(5), nullable=True),
        sa.Column("description_ka", sa.Text(), nullable=False, server_default=""),
        sa.Column("description_ru", sa.Text(), nullable=False, server_default=""),
        sa.Column("description_en", sa.Text(), nullable=False, server_default=""),
        sa.Column("images", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("whatsapp", sa.String(20), nullable=True),
        sa.Column("contact_url", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fraud_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fraud_reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("min_price_gel", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_guests", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )
    op.create_index("ix_bina_hotels_city", "bina_hotels", ["city"])
    op.create_index("ix_bina_hotels_owner_user_id", "bina_hotels", ["owner_user_id"])
    op.create_table(
        "bina_hotel_rooms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "hotel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_hotels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("title", sa.String(120), nullable=False, server_default=""),
        sa.Column("guests", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GEL"),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        *_timestamps(),
    )
    op.create_index("ix_bina_hotel_rooms_hotel_id", "bina_hotel_rooms", ["hotel_id"])
    op.create_table(
        "bina_hotel_complaints",
        sa.Column(
            "hotel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_hotels.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bina_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )


def downgrade() -> None:
    op.drop_table("bina_hotel_complaints")
    op.drop_table("bina_hotel_rooms")
    op.drop_table("bina_hotels")
