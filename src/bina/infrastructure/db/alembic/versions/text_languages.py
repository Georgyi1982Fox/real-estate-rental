"""Move listing texts to the column of the language they are written in (TASK-019).

Раньше текст с русской страницы сайта сохранялся в ``*_ru``, даже если хозяин
написал его по-грузински. Здесь каждый заголовок и описание переезжает в колонку
своего языка (по письменности); освободившиеся колонки заново заполнит перевод.

Revision ID: text_languages
Revises: district_names
Create Date: 2026-09-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from bina.application.localization import script_of

# revision identifiers, used by Alembic.
revision = "text_languages"
down_revision = "district_names"
branch_labels = None
depends_on = None

LANGUAGES = ("ru", "ka", "en")
COLUMNS = [f"{kind}_{lang}" for kind in ("title", "description") for lang in LANGUAGES]


def fixes(row: dict[str, str | None]) -> dict[str, str]:
    """Новые значения колонок строки (пусто — всё на своих местах)."""
    values = {column: row.get(column) or "" for column in COLUMNS}
    changed: dict[str, str] = {}
    for kind in ("title", "description"):
        for lang in LANGUAGES:
            column = f"{kind}_{lang}"
            text = values[column]
            if not text.strip():
                continue
            actual = script_of(text)
            if actual == lang:
                continue
            target = f"{kind}_{actual}"
            if not values[target].strip():
                values[target] = text
                changed[target] = text
            values[column] = ""
            changed[column] = ""
    return changed


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(f"SELECT id, {', '.join(COLUMNS)} FROM bina_listings")
    ).mappings()
    for row in list(rows):
        changed = fixes(dict(row))
        if changed:
            assignments = ", ".join(f"{column} = :{column}" for column in changed)
            connection.execute(
                sa.text(f"UPDATE bina_listings SET {assignments} WHERE id = :id"),
                {**changed, "id": row["id"]},
            )


def downgrade() -> None:
    # Переносы не откатываем: тексты на своих языках ничему не мешают
    pass
