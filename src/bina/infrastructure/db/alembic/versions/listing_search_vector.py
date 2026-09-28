"""Full-text search vector for listings (TASK-022).

Revision ID: listing_search_vector
Revises: saved_searches_notifications
Create Date: 2026-09-28

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_search_vector"
down_revision = "saved_searches_notifications"
branch_labels = None
depends_on = None

# Заголовок важнее описания (вес A и B). Русский и английский — со словоформами,
# грузинский — без (в PostgreSQL нет грузинского словаря), поиск по началу слова.
SEARCH_VECTOR = """
    setweight(to_tsvector('russian', coalesce(title_ru, '')), 'A')
    || setweight(to_tsvector('english', coalesce(title_en, '')), 'A')
    || setweight(to_tsvector('simple', coalesce(title_ka, '')), 'A')
    || setweight(to_tsvector('russian', coalesce(description_ru, '')), 'B')
    || setweight(to_tsvector('english', coalesce(description_en, '')), 'B')
    || setweight(to_tsvector('simple', coalesce(description_ka, '')), 'B')
"""


def upgrade() -> None:
    # Вычисляемый столбец: PostgreSQL сам обновляет его при изменении текста
    op.execute(
        f"ALTER TABLE bina_listings ADD COLUMN search_vector tsvector "
        f"GENERATED ALWAYS AS ({SEARCH_VECTOR}) STORED"
    )
    op.execute(
        "CREATE INDEX ix_bina_listings_search_vector_all ON bina_listings USING gin (search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bina_listings_search_vector_all")
    op.execute("ALTER TABLE bina_listings DROP COLUMN IF EXISTS search_vector")
