"""Дозагрузка подробностей и проверка старых объявлений (TASK-018).

Раньше SS.ge разбирался только по страницам списка: у таких объявлений нет
полного описания, удобств, этажности. Здесь для них по одному открывается
страница объявления.

Кроме того, заново открываются объявления, которых давно не было в списке
сайта (``checked_at`` старше ``recheck_before``): парсер смотрит только первые
страницы поиска, поэтому снятое объявление иначе так и осталось бы в поиске.
Объявление, которого на сайте больше нет (404/410, перенаправление на другую
страницу или отметка «неактивно» на странице), уходит в архив.
"""

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import httpx
import structlog
from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.models import Listing, ListingStatus
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.scrapers.base_scraper import ListingGoneError
from bina.infrastructure.scrapers.normalizer import ListingNormalizer

logger = structlog.get_logger(__name__)

GONE_STATUSES = {404, 410}


class DetailsSource(Protocol):
    """Парсер, умеющий разобрать страницу объявления."""

    async def _fetch_page(self, url: str, expect: str | None = None) -> str: ...

    def details_from_html(self, html: str) -> dict[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class BackfillStats:
    """Итог дозагрузки."""

    checked: int
    updated: int
    archived: int
    failed: int


def raw_from_listing(listing: Listing) -> RawListing:
    """Объявление из БД в виде ``RawListing`` (основа для слияния с подробностями)."""
    language = "ru" if listing.title_ru else "ka"
    district = listing.district
    return RawListing(
        source_id=listing.source_id,
        source_name=listing.source_name,
        title=getattr(listing, f"title_{language}") or "",
        description=getattr(listing, f"description_{language}") or "",
        price=float(listing.price),
        currency=listing.currency,
        rooms=listing.rooms,
        area=float(listing.area),
        district=(district.name_ru or district.name_ka) if district is not None else "Unknown",
        url=listing.url or "",
        photos=list(listing.images or []),
        phone=listing.phone,
        owner_name=listing.owner_name,
        language=language,
    )


async def backfill_details(
    session_factory: async_sessionmaker[AsyncSession],
    sources: dict[str, DetailsSource],
    limit: int,
    recheck_before: datetime | None = None,
) -> BackfillStats:
    """Открывает страницы до ``limit`` объявлений.

    Сначала — без подробностей (новые сверху), затем — не виденные на сайте с
    ``recheck_before`` (давние первыми).
    """
    stale: ColumnElement[bool] = Listing.details_fetched_at.is_(None)
    if recheck_before is not None:
        stale = or_(stale, Listing.checked_at.is_(None), Listing.checked_at < recheck_before)
    async with session_factory() as session:
        query = (
            select(Listing)
            .options(selectinload(Listing.district))
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                stale,
                Listing.url.is_not(None),
                Listing.source_name.in_(list(sources)),
            )
            .order_by(
                Listing.details_fetched_at.is_not(None),
                Listing.checked_at.asc().nulls_first(),
                Listing.created_at.desc(),
            )
            .limit(limit)
        )
        cards = [raw_from_listing(item) for item in (await session.execute(query)).scalars()]

    normalizer = ListingNormalizer()
    updated = archived = failed = 0
    for card in cards:
        source = sources[card.source_name]
        try:
            html = await source._fetch_page(card.url, expect=card.source_id)
        except ListingGoneError:
            await _archive(session_factory, card)
            archived += 1
            continue
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in GONE_STATUSES:
                await _archive(session_factory, card)
                archived += 1
            else:
                failed += 1
                await _mark_checked(session_factory, card)
                logger.warning("Detail page failed", url=card.url, error=str(exc))
            continue
        except httpx.HTTPError as exc:
            # Сеть: не отмечаем, попробуем в следующий раз
            failed += 1
            logger.warning("Detail page failed", url=card.url, error=str(exc))
            continue

        details = source.details_from_html(html)
        raw = normalizer.normalize_listing(dataclasses.replace(card, **(details or {})))
        if details is None or raw is None:
            failed += 1
            # Отметка, чтобы неразборчивая страница не занимала очередь каждый запуск
            await _mark_checked(session_factory, card)
            logger.warning("Detail page not parsed", url=card.url)
            continue
        async with session_factory() as session:
            await ListingsRepository(session).create_or_update_from_raw(raw)
            await session.commit()
        if raw.active:
            updated += 1
        else:
            archived += 1
            logger.info("Listing inactive on source, archived", url=card.url)

    stats = BackfillStats(checked=len(cards), updated=updated, archived=archived, failed=failed)
    logger.info(
        "Details backfill finished",
        checked=stats.checked,
        updated=updated,
        archived=archived,
        failed=failed,
    )
    return stats


async def _mark_checked(
    session_factory: async_sessionmaker[AsyncSession], card: RawListing
) -> None:
    """Проверка не удалась, но объявление откладывается до следующего круга."""
    async with session_factory() as session:
        await ListingsRepository(session).mark_checked(card.source_name, [card.source_id])
        await session.commit()


async def _archive(session_factory: async_sessionmaker[AsyncSession], card: RawListing) -> None:
    """Объявления больше нет на сайте: в архив (не в поиске и не в уведомлениях)."""
    async with session_factory() as session:
        listing = await ListingsRepository(session).find_by_source(card.source_id, card.source_name)
        if listing is not None:
            listing.status = ListingStatus.ARCHIVED
            await session.commit()
    logger.info("Listing removed on source, archived", url=card.url)
