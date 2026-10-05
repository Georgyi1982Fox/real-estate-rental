"""Retry every listing whose translation failed (AI outages were marked as failures).

Revision ID: retry_translations
Revises: history_notes
Create Date: 2026-10-05

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "retry_translations"
down_revision = "history_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE bina_listings SET translation_failed_at = NULL")


def downgrade() -> None:
    pass
