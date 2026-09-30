"""One embedding per listing (TASK-012).

Revision ID: embeddings_unique
Revises: district_city
Create Date: 2026-09-30

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "embeddings_unique"
down_revision = "district_city"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Повторы (старый код мог сохранить два) — оставляем самый свежий
    op.execute("""
        DELETE FROM bina_embeddings AS e
        USING bina_embeddings AS newer
        WHERE e.listing_id = newer.listing_id
          AND (e.updated_at, e.id) < (newer.updated_at, newer.id)
    """)
    op.create_index("ux_bina_embeddings_listing_id", "bina_embeddings", ["listing_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_bina_embeddings_listing_id", table_name="bina_embeddings")
