"""Объявления собственников (TASK-096): создание, список, снятие, цена, фото."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, String, cast, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bina.application.chat import chat_link
from bina.application.owner_listings import (
    OWNER_SOURCE,
    OwnerListingDraft,
    owner_raw_listing,
)
from bina.infrastructure.db.models import Listing, ListingStatus
from bina.infrastructure.db.repositories.listings import ListingsRepository


class OwnerListingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _owned(self, user_id: UUID) -> list[ColumnElement[bool]]:
        return [
            Listing.owner_user_id == user_id,
            Listing.source_name == OWNER_SOURCE,
            Listing.is_deleted.is_(False),
        ]

    async def count_active(self, user_id: UUID) -> int:
        query = select(func.count()).where(
            *self._owned(user_id), Listing.status == ListingStatus.ACTIVE
        )
        return int((await self._session.execute(query)).scalar_one())

    async def list_for_user(self, user_id: UUID) -> list[Listing]:
        """Объявления человека: активные сверху, затем новые."""
        query = (
            select(Listing)
            .options(selectinload(Listing.district))
            .where(*self._owned(user_id))
            .order_by(Listing.status != ListingStatus.ACTIVE, Listing.created_at.desc())
        )
        return list((await self._session.execute(query)).scalars().all())

    async def get_owned(self, user_id: UUID, listing_id: UUID) -> Listing | None:
        query = (
            select(Listing)
            .options(selectinload(Listing.district))
            .where(*self._owned(user_id), Listing.id == listing_id)
        )
        return (await self._session.execute(query)).scalar_one_or_none()

    async def create(
        self,
        user_id: UUID,
        draft: OwnerListingDraft,
        source_id: str,
        photos: list[str],
        now: datetime,
    ) -> Listing:
        """Новое объявление: как с сайта, плюс хозяин."""
        raw = owner_raw_listing(draft, source_id, photos, now)
        # Заголовки на трёх языках ставит сам create_or_update_from_raw (listing_titles)
        listing = await ListingsRepository(self._session).create_or_update_from_raw(raw)
        listing.owner_user_id = user_id
        await self._session.flush()
        await self._session.refresh(listing, attribute_names=["district"])
        return listing

    async def set_active(self, listing: Listing, active: bool, now: datetime) -> None:
        """Снять с публикации (сдано) или вернуть в поиск."""
        listing.status = ListingStatus.ACTIVE if active else ListingStatus.ARCHIVED
        if active:
            # Вернули — как свежее объявление
            listing.source_updated_at = now
        await self._session.flush()

    async def set_url(self, listing: Listing, url: str) -> None:
        listing.url = url
        await self._session.flush()

    async def link_to_chat(self, bot_username: str) -> int:
        """Кнопка «Написать» у всех объявлений хозяев — в чат через бота (TASK-111)."""
        prefix = chat_link(bot_username, "")
        result = await self._session.execute(
            update(Listing)
            .where(
                Listing.source_name == OWNER_SOURCE,
                or_(Listing.url.is_(None), Listing.url.not_like(f"{prefix}%")),
            )
            .values(url=func.concat(prefix, cast(Listing.id, String)))
            .returning(Listing.id)
        )
        return len(result.all())

    async def update_price(
        self, listing: Listing, price: Decimal, currency: str, now: datetime
    ) -> None:
        """Новая цена; снижение попадёт в уведомления «цена снижена» (TASK-028)."""
        if Decimal(listing.price) != price or listing.currency != currency:
            listing.previous_price = listing.price if listing.currency == currency else None
            listing.price_changed_at = now
            listing.price = price
            listing.currency = currency
            listing.source_updated_at = now
            # С новой ценой — заново дубликаты и антифрод
            listing.duplicates_checked_at = None
            listing.fraud_checked_at = None
        await self._session.flush()

    async def set_photos(self, listing: Listing, photos: list[str]) -> None:
        listing.images = list(photos)
        listing.fraud_checked_at = None
        await self._session.flush()
