"""Remove HTML tags (<br />) from listing texts (TASK-019).

MyHome отдаёт описание с HTML: ``<br />`` показывались в приложении как есть.

Revision ID: clean_html_texts
Revises: text_languages
Create Date: 2026-09-29

"""

from __future__ import annotations

import re

import sqlalchemy as sa
from alembic import op

from bina.application.text import html_to_text

# revision identifiers, used by Alembic.
revision = "clean_html_texts"
down_revision = "text_languages"
branch_labels = None
depends_on = None

COLUMNS = [f"{kind}_{lang}" for kind in ("title", "description") for lang in ("ru", "ka", "en")]


def clean(text: str) -> str:
    """Как нормализатор парсера: без тегов, без лишних пробелов, абзацы сохранены."""
    lines = [re.sub(r"[ \t\f\v\r]+", " ", line).strip() for line in html_to_text(text).split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def upgrade() -> None:
    connection = op.get_bind()
    condition = " OR ".join(f"{column} ~ '<[a-zA-Z/]|&[a-z]+;'" for column in COLUMNS)
    rows = connection.execute(
        sa.text(f"SELECT id, {', '.join(COLUMNS)} FROM bina_listings WHERE {condition}")
    ).mappings()
    for row in list(rows):
        changed = {
            column: clean(row[column])
            for column in COLUMNS
            if row[column] and clean(row[column]) != row[column]
        }
        if changed:
            assignments = ", ".join(f"{column} = :{column}" for column in changed)
            connection.execute(
                sa.text(f"UPDATE bina_listings SET {assignments} WHERE id = :id"),
                {**changed, "id": row["id"]},
            )


def downgrade() -> None:
    pass
