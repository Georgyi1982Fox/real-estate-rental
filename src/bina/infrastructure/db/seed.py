"""Загрузка демо-данных (районы и квартиры) для локальной разработки.

Источник по умолчанию: ``frontend/mock_data.json`` (демо-данные фронтенда).
Квартиры помечаются ``source_name="demo"``, поэтому их легко отличить от
настоящих объявлений парсера и удалить командой ``bina-seed --reset``.

Запуск: ``bina-seed`` (из корня репозитория, нужен ``DATABASE_URL``).
"""

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import click
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.models import District, Favorite, Listing, ListingStatus
from bina.infrastructure.db.session.manager import DatabaseManager

DEMO_SOURCE = "demo"
DEFAULT_FILE = Path("frontend/mock_data.json")
DEFAULT_SAFETY_SCORE = 5


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Итог загрузки."""

    districts_created: int
    listings_created: int
    listings_updated: int


def _text(value: Any, language: str) -> str:
    """Перевод из ``{"ka": ..., "ru": ..., "en": ...}`` или строка как есть."""
    if isinstance(value, dict):
        return str(value.get(language) or "")
    return str(value or "")


async def _upsert_districts(
    session: AsyncSession,
    data: dict[str, Any],
) -> tuple[dict[str, District], int]:
    """Находит районы по английскому названию или создаёт их. Возвращает ``{slug: District}``."""
    prices: dict[str, list[Decimal]] = defaultdict(list)
    for item in data.get("listings", []):
        if item.get("area"):
            price = Decimal(str(item["price"]))
            prices[item["district"]].append(price / Decimal(str(item["area"])))

    by_slug: dict[str, District] = {}
    created = 0
    for item in data.get("districts", []):
        name = item["name"]
        name_en = _text(name, "en") or item["id"]
        district = (
            await session.execute(select(District).where(District.name_en == name_en))
        ).scalar_one_or_none()
        if district is None:
            per_m2 = prices.get(item["id"]) or [Decimal(0)]
            district = District(
                name_ru=_text(name, "ru") or name_en,
                name_ka=_text(name, "ka") or name_en,
                name_en=name_en,
                avg_price_per_m2=round(sum(per_m2) / len(per_m2), 2),
                safety_score=DEFAULT_SAFETY_SCORE,
            )
            session.add(district)
            created += 1
        by_slug[item["id"]] = district
    await session.flush()
    return by_slug, created


async def load_demo_data(session: AsyncSession, data: dict[str, Any]) -> SeedResult:
    """Загружает районы и квартиры; повторный запуск обновляет, а не дублирует.

    Не коммитит: транзакцией управляет вызывающий код.

    Raises:
        ValueError: если у квартиры указан район, которого нет в ``districts``.
    """
    districts, districts_created = await _upsert_districts(session, data)
    now = datetime.now(UTC)
    created = updated = 0

    for item in data.get("listings", []):
        district = districts.get(item["district"])
        if district is None:
            raise ValueError(f"Listing {item['id']}: unknown district {item['district']!r}")

        source_id = f"{DEMO_SOURCE}-{item['id']}"
        values = {
            "title_ru": _text(item["title"], "ru"),
            "title_ka": _text(item["title"], "ka"),
            "description_ru": _text(item.get("description"), "ru"),
            "description_ka": _text(item.get("description"), "ka"),
            "price": Decimal(str(item["price"])),
            "currency": item.get("currency", "GEL"),
            "district_id": district.id,
            "rooms": int(item["rooms"]),
            "area": Decimal(str(item["area"])),
            "status": ListingStatus.ACTIVE,
            "is_deleted": False,
        }
        listing = (
            await session.execute(
                select(Listing).where(
                    Listing.source_id == source_id, Listing.source_name == DEMO_SOURCE
                )
            )
        ).scalar_one_or_none()
        if listing is None:
            # Порядок как в файле: первая квартира самая «новая»
            listing = Listing(
                source_id=source_id,
                source_name=DEMO_SOURCE,
                created_at=now - timedelta(minutes=int(item["id"])),
                **values,
            )
            session.add(listing)
            created += 1
        else:
            for key, value in values.items():
                setattr(listing, key, value)
            updated += 1

    await session.flush()
    return SeedResult(districts_created, created, updated)


async def delete_demo_data(session: AsyncSession) -> int:
    """Удаляет демо-квартиры (и их записи в избранном). Районы остаются.

    Returns:
        Количество удалённых квартир.
    """
    demo_ids = select(Listing.id).where(Listing.source_name == DEMO_SOURCE)
    await session.execute(delete(Favorite).where(Favorite.listing_id.in_(demo_ids)))
    result = await session.execute(delete(Listing).where(Listing.source_name == DEMO_SOURCE))
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


async def _run(file: Path, reset: bool) -> str:
    db = DatabaseManager()
    try:
        async with db.session_factory() as session:
            if reset:
                removed = await delete_demo_data(session)
                await session.commit()
                return f"Удалено демо-квартир: {removed}"
            data = json.loads(file.read_text(encoding="utf-8"))
            result = await load_demo_data(session, data)
            await session.commit()
            return (
                f"Районов создано: {result.districts_created}; "
                f"квартир создано: {result.listings_created}, обновлено: {result.listings_updated}"
            )
    finally:
        await db.dispose()


@click.command()
@click.option(
    "--file",
    "file",
    type=click.Path(path_type=Path),
    default=DEFAULT_FILE,
    show_default=True,
    help="JSON с ключами districts и listings.",
)
@click.option("--reset", is_flag=True, help="Удалить демо-квартиры вместо загрузки.")
def cli(file: Path, reset: bool) -> None:
    """Загрузить демо-данные в базу (DATABASE_URL). Повторный запуск безопасен."""
    if not reset and not file.is_file():
        raise click.ClickException(
            f"Файл {file} не найден. Запустите команду из корня репозитория или укажите --file."
        )
    click.echo(asyncio.run(_run(file, reset)))


if __name__ == "__main__":
    cli()
