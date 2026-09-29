"""District names in ka/ru/en for districts created by the parser (TASK-019).

Парсер создавал районы с одним и тем же названием на всех языках. Здесь им
проставляются названия из словаря районов Тбилиси (или транслитерация).

Revision ID: district_names
Revises: listing_details
Create Date: 2026-09-29

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from bina.application.localization import district_names

# revision identifiers, used by Alembic.
revision = "district_names"
down_revision = "listing_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, name_ru, name_ka, name_en FROM bina_districts "
            "WHERE name_ru = name_en OR name_ru = name_ka OR name_ka = name_en"
        )
    ).all()
    for district_id, name_ru, name_ka, name_en in rows:
        names = district_names(name_ru or name_en or name_ka)
        if not names:
            continue
        connection.execute(
            sa.text(
                "UPDATE bina_districts SET name_ru = :ru, name_ka = :ka, name_en = :en "
                "WHERE id = :id"
            ),
            {"ru": names["ru"], "ka": names["ka"], "en": names["en"], "id": district_id},
        )


def downgrade() -> None:
    # Старые одинаковые названия не восстанавливаем: новые им не мешают
    pass
