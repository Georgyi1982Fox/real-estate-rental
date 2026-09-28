"""Saved searches, notifications and listing price history (TASK-028).

Revision ID: saved_searches_notifications
Revises: listing_translations_en
Create Date: 2026-09-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "saved_searches_notifications"
down_revision = "listing_translations_en"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")


def upgrade() -> None:
    # Предыдущая цена: из неё уведомление «цена снижена»
    op.add_column("bina_listings", sa.Column("previous_price", sa.Numeric(), nullable=True))
    op.add_column(
        "bina_listings",
        sa.Column("price_changed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "bina_saved_searches",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id", UUID, sa.ForeignKey("bina_users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("district_id", UUID, sa.ForeignKey("bina_districts.id"), nullable=True),
        sa.Column("price_min", sa.Numeric(), nullable=True),
        sa.Column("price_max", sa.Numeric(), nullable=True),
        sa.Column("rooms", sa.Integer(), nullable=True),
        sa.Column("notify", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_since", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_saved_searches_user_id", "bina_saved_searches", ["user_id"])

    op.create_table(
        "bina_notifications",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id", UUID, sa.ForeignKey("bina_users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column(
            "listing_id",
            UUID,
            sa.ForeignKey("bina_listings.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "search_id",
            UUID,
            sa.ForeignKey("bina_saved_searches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("old_price", sa.Numeric(), nullable=True),
        sa.Column("new_price", sa.Numeric(), nullable=True),
        sa.Column("text", sa.JSON(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index(
        "ix_notifications_user_created", "bina_notifications", ["user_id", "created_at"]
    )
    # Не больше одного уведомления о новой квартире на пользователя
    # и одного о снижении до конкретной цены
    op.create_index(
        "uq_notifications_new_listing",
        "bina_notifications",
        ["user_id", "listing_id"],
        unique=True,
        postgresql_where=sa.text("type = 'new_listing'"),
    )
    op.create_index(
        "uq_notifications_price_drop",
        "bina_notifications",
        ["user_id", "listing_id", "new_price"],
        unique=True,
        postgresql_where=sa.text("type = 'price_drop'"),
    )
    # Очередь отправки в Telegram
    op.create_index(
        "ix_notifications_unsent",
        "bina_notifications",
        ["created_at"],
        postgresql_where=sa.text("sent_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("bina_notifications")
    op.drop_table("bina_saved_searches")
    op.drop_column("bina_listings", "price_changed_at")
    op.drop_column("bina_listings", "previous_price")
