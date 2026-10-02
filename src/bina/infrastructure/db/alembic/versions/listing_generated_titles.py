"""Titles of all listings built from their data in ka/ru/en.

Заголовки сайтов были на одном языке и ждали перевода AI; теперь заголовок
собирается из комнат, района и площади (bina.application.listing_titles). Здесь —
то же самое для уже сохранённых объявлений, одним запросом.

Revision ID: listing_generated_titles
Revises: listing_owner
Create Date: 2026-10-01

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "listing_generated_titles"
down_revision = "listing_owner"
branch_labels = None
depends_on = None

# Шаблоны совпадают с bina.application.listing_titles (проверяется тестом)
TITLES = {
    "ru": ("'Посуточно: '", "'-комн. квартира, '", "' м²'"),
    "en": ("'Daily: '", "'-room apartment, '", "' m²'"),
    "ka": ("'დღიურად: '", "'-ოთახიანი ბინა, '", "' მ²'"),
}


def _title(language: str) -> str:
    daily, rooms, area = TITLES[language]
    district = f"coalesce(nullif(d.name_{language}, ''), d.name_ru)"
    return (
        f"(CASE WHEN l.rent_period = 'daily' THEN {daily} ELSE '' END)"
        f" || l.rooms || {rooms} || {district} || ', '"
        f" || trim_scale(l.area)::text || {area}"
    )


def upgrade() -> None:
    op.execute(f"""
        UPDATE bina_listings AS l
        SET title_ru = {_title("ru")},
            title_en = {_title("en")},
            title_ka = {_title("ka")}
        FROM bina_districts AS d
        WHERE d.id = l.district_id
    """)


def downgrade() -> None:
    # Заголовки сайтов не сохранялись отдельно: вернуть их нельзя (и не нужно)
    pass
