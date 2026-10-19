"""«Весь город» вместо района с названием города (TASK-122).

Сайты не всегда указывают район, и парсеры писали вместо него город («Батуми»,
«Районы Батуми», «Unknown»): получался «район Батуми» в списке районов Батуми. Такие
районы одного города склеиваются в один «весь город» (``is_city_wide``, название — город):
объявления и сохранённые поиски переходят в него, остальные копии скрываются.

Revision ID: city_wide_districts
Revises: hotel_chat
Create Date: 2026-10-19

"""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from alembic import op

from bina.application.cities import CITIES
from bina.application.localization import is_city_wide_district

# revision identifiers, used by Alembic.
revision = "city_wide_districts"
down_revision = "hotel_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bina_districts",
        sa.Column("is_city_wide", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    merge_city_wide(op.get_bind())


def merge_city_wide(bind: sa.Connection) -> None:
    """Районы-«города» каждого города — в один «весь город» (отдельно — для теста)."""
    rows = bind.execute(
        sa.text(
            "SELECT id, city, name_ka, name_ru, name_en FROM bina_districts "
            "WHERE is_deleted = false ORDER BY created_at, id"
        )
    ).all()
    groups: dict[str, list[UUID]] = {}
    for row in rows:
        # Пустое название — не «город»: просто нет перевода
        if row.city in CITIES and any(
            name and is_city_wide_district(name, row.city)
            for name in (row.name_ru, row.name_en, row.name_ka)
        ):
            groups.setdefault(row.city, []).append(row.id)
    for code, ids in groups.items():
        keep, *others = ids
        names = CITIES[code].names
        bind.execute(
            sa.text(
                "UPDATE bina_districts SET is_city_wide = true, name_ka = :ka, name_ru = :ru, "
                "name_en = :en WHERE id = :id"
            ),
            {"id": keep, "ka": names["ka"], "ru": names["ru"], "en": names["en"]},
        )
        for old in others:
            values = {"old": old, "new": keep}
            bind.execute(
                sa.text("UPDATE bina_listings SET district_id = :new WHERE district_id = :old"),
                values,
            )
            bind.execute(
                sa.text(
                    "UPDATE bina_saved_searches SET district_id = :new WHERE district_id = :old"
                ),
                values,
            )
            bind.execute(
                sa.text(
                    "UPDATE bina_saved_searches "
                    "SET district_ids = array_replace(district_ids, :old, :new) "
                    "WHERE :old = ANY(district_ids)"
                ),
                values,
            )
            bind.execute(
                sa.text(
                    "UPDATE bina_districts SET is_deleted = true, deleted_at = now() "
                    "WHERE id = :old"
                ),
                {"old": old},
            )


def downgrade() -> None:
    # Склеенные копии остаются скрытыми: объявления уже в одном «районе»
    op.drop_column("bina_districts", "is_city_wide")
