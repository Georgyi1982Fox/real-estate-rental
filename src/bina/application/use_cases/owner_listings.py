"""Размещение и изменение объявлений собственниками (TASK-096)."""

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import structlog

from bina.application.chat import chat_link
from bina.application.owner_listings import (
    BAD_PHOTO,
    DAILY_LIMIT,
    EXTRA_NEW_PER_DAY,
    LIMIT_REACHED,
    MAX_ACTIVE_LISTINGS,
    MAX_PHOTOS,
    NO_CONTACT,
    NOT_FOUND,
    TOO_MANY_PHOTOS,
    OwnerListingDraft,
    OwnerListingError,
)
from bina.application.ports.photo_storage import IPhotoStorage, PhotoError
from bina.infrastructure.db.models import Listing, ListingStatus

logger = structlog.get_logger(__name__)


class IOwnerListingsRepository(Protocol):
    async def count_active(self, user_id: UUID) -> int: ...

    async def count_created_since(self, user_id: UUID, since: datetime) -> int: ...

    async def list_for_user(self, user_id: UUID) -> list[Listing]: ...

    async def get_owned(self, user_id: UUID, listing_id: UUID) -> Listing | None: ...

    async def create(
        self,
        user_id: UUID,
        draft: OwnerListingDraft,
        source_id: str,
        photos: list[str],
        now: datetime,
    ) -> Listing: ...

    async def set_active(self, listing: Listing, active: bool, now: datetime) -> None: ...

    async def update_price(
        self, listing: Listing, price: Decimal, currency: str, now: datetime
    ) -> None: ...

    async def set_photos(self, listing: Listing, photos: list[str]) -> None: ...

    async def set_url(self, listing: Listing, url: str) -> None: ...


class OwnerListingsUseCase:
    """Всё, что собственник делает со своими объявлениями (бот и API)."""

    def __init__(self, repository: IOwnerListingsRepository, storage: IPhotoStorage) -> None:
        self._repository = repository
        self._storage = storage

    async def publish(
        self,
        user_id: UUID,
        draft: OwnerListingDraft,
        photos: Sequence[bytes],
        now: datetime,
        bot_username: str | None = None,
        max_active: int = MAX_ACTIVE_LISTINGS,
    ) -> Listing:
        """Новое объявление — сразу в поиске.

        ``bot_username`` — кнопка «Написать» ведёт в чат с хозяином через бота (TASK-111),
        а не в личный Telegram хозяина.

        Raises:
            OwnerListingError: лимит объявлений, нет контакта, слишком много фото.
        """
        if await self._repository.count_active(user_id) >= max_active:
            raise OwnerListingError(LIMIT_REACHED)
        created = await self._repository.count_created_since(user_id, now - timedelta(days=1))
        if created >= max_active + EXTRA_NEW_PER_DAY:
            raise OwnerListingError(DAILY_LIMIT)
        if not draft.phone and not draft.contact_url:
            raise OwnerListingError(NO_CONTACT)
        if len(photos) > MAX_PHOTOS:
            raise OwnerListingError(TOO_MANY_PHOTOS)
        source_id = uuid.uuid4().hex
        urls: list[str] = []
        for data in photos:
            try:
                urls.append(self._storage.save(source_id, data))
            except PhotoError as exc:
                # Одно битое фото не должно сорвать всё объявление
                logger.warning("Owner photo skipped", error=str(exc))
        listing = await self._repository.create(user_id, draft, source_id, urls, now)
        if bot_username:
            await self._repository.set_url(listing, chat_link(bot_username, listing.id))
        logger.info("Owner listing published", listing_id=str(listing.id), photos=len(urls))
        return listing

    async def owned(self, user_id: UUID, listing_id: UUID) -> Listing:
        listing = await self._repository.get_owned(user_id, listing_id)
        if listing is None:
            raise OwnerListingError(NOT_FOUND)
        return listing

    async def set_active(
        self,
        user_id: UUID,
        listing_id: UUID,
        active: bool,
        now: datetime,
        max_active: int = MAX_ACTIVE_LISTINGS,
    ) -> Listing:
        listing = await self.owned(user_id, listing_id)
        if active and listing.status != ListingStatus.ACTIVE:
            if await self._repository.count_active(user_id) >= max_active:
                raise OwnerListingError(LIMIT_REACHED)
        await self._repository.set_active(listing, active, now)
        return listing

    async def update_price(
        self, user_id: UUID, listing_id: UUID, price: Decimal, currency: str, now: datetime
    ) -> Listing:
        listing = await self.owned(user_id, listing_id)
        await self._repository.update_price(listing, price, currency, now)
        return listing

    async def add_photo(self, user_id: UUID, listing_id: UUID, data: bytes) -> Listing:
        """Ещё одно фото (Mini App загружает по одному)."""
        listing = await self.owned(user_id, listing_id)
        photos = list(listing.images or [])
        if len(photos) >= MAX_PHOTOS:
            raise OwnerListingError(TOO_MANY_PHOTOS)
        try:
            url = self._storage.save(listing.source_id, data)
        except PhotoError as exc:
            raise OwnerListingError(BAD_PHOTO) from exc
        await self._repository.set_photos(listing, [*photos, url])
        return listing

    async def delete_photo(self, user_id: UUID, listing_id: UUID, index: int) -> Listing:
        listing = await self.owned(user_id, listing_id)
        photos = list(listing.images or [])
        if not 0 <= index < len(photos):
            raise OwnerListingError(NOT_FOUND)
        removed = photos.pop(index)
        await self._repository.set_photos(listing, photos)
        self._storage.delete(removed)
        return listing
