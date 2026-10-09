"""Размещение гостиниц хозяином (TASK-120): лимиты, проверка правилами, номера, фото."""

from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from bina.application.hotels import (
    BAD_PHOTO,
    DAILY_LIMIT,
    LIMIT_REACHED,
    MAX_ACTIVE_HOTELS,
    MAX_NEW_PER_DAY,
    MAX_PHOTOS,
    MAX_ROOMS,
    NO_CONTACT,
    NOT_FOUND,
    REJECTED,
    TOO_MANY_PHOTOS,
    TOO_MANY_ROOMS,
    HotelDraft,
    HotelError,
    RoomDraft,
    problems,
    room_problems,
)
from bina.application.ports.photo_storage import IPhotoStorage, PhotoError


class IHotelsRepository(Protocol):
    async def create(self, owner_id: UUID, draft: HotelDraft) -> Any: ...
    async def owned(self, owner_id: UUID, hotel_id: UUID) -> Any | None: ...
    async def count_active(self, owner_id: UUID) -> int: ...
    async def count_created_since(self, owner_id: UUID, since: datetime) -> int: ...
    async def delete(self, hotel: Any) -> None: ...


class IHotelEditor(Protocol):
    """Изменение уже загруженного объекта (функции репозитория)."""

    def apply(self, hotel: Any, draft: HotelDraft) -> None: ...
    def add_room(self, hotel: Any, room: RoomDraft) -> Any: ...
    def update_room(self, hotel: Any, room_id: UUID, room: RoomDraft) -> bool: ...
    def remove_room(self, hotel: Any, room_id: UUID) -> bool: ...


class HotelsUseCase:
    def __init__(
        self, repository: IHotelsRepository, editor: IHotelEditor, photos: IPhotoStorage
    ) -> None:
        self._repository = repository
        self._editor = editor
        self._photos = photos

    async def publish(self, owner_id: UUID, draft: HotelDraft, now: datetime) -> Any:
        """Разместить объект: сразу в поиске, если прошёл проверку правилами."""
        if not draft.phone and not draft.contact_url:
            raise HotelError(NO_CONTACT)
        if len(draft.rooms) > MAX_ROOMS:
            raise HotelError(TOO_MANY_ROOMS)
        self._check(draft)
        if await self._repository.count_active(owner_id) >= MAX_ACTIVE_HOTELS:
            raise HotelError(LIMIT_REACHED)
        since = now - timedelta(days=1)
        if await self._repository.count_created_since(owner_id, since) >= MAX_NEW_PER_DAY:
            raise HotelError(DAILY_LIMIT)
        return await self._repository.create(owner_id, draft)

    async def owned(self, owner_id: UUID, hotel_id: UUID) -> Any:
        hotel = await self._repository.owned(owner_id, hotel_id)
        if hotel is None:
            raise HotelError(NOT_FOUND)
        return hotel

    async def update(self, owner_id: UUID, hotel_id: UUID, draft: HotelDraft) -> Any:
        """Новые данные объекта (номера и фото не меняются)."""
        hotel = await self.owned(owner_id, hotel_id)
        if not draft.phone and not draft.contact_url:
            raise HotelError(NO_CONTACT)
        self._check(draft)
        self._editor.apply(hotel, draft)
        return hotel

    async def set_active(self, owner_id: UUID, hotel_id: UUID, active: bool) -> Any:
        hotel = await self.owned(owner_id, hotel_id)
        if active and not hotel.is_active:
            if await self._repository.count_active(owner_id) >= MAX_ACTIVE_HOTELS:
                raise HotelError(LIMIT_REACHED)
        hotel.is_active = active
        return hotel

    async def delete(self, owner_id: UUID, hotel_id: UUID) -> None:
        hotel = await self.owned(owner_id, hotel_id)
        for url in list(hotel.images or []):
            self._photos.delete(url)
        await self._repository.delete(hotel)

    async def add_room(self, owner_id: UUID, hotel_id: UUID, room: RoomDraft) -> Any:
        hotel = await self.owned(owner_id, hotel_id)
        if len(hotel.rooms) >= MAX_ROOMS:
            raise HotelError(TOO_MANY_ROOMS)
        self._check_room(room)
        self._editor.add_room(hotel, room)
        return hotel

    async def update_room(
        self, owner_id: UUID, hotel_id: UUID, room_id: UUID, room: RoomDraft
    ) -> Any:
        hotel = await self.owned(owner_id, hotel_id)
        self._check_room(room)
        if not self._editor.update_room(hotel, room_id, room):
            raise HotelError(NOT_FOUND)
        return hotel

    async def remove_room(self, owner_id: UUID, hotel_id: UUID, room_id: UUID) -> Any:
        hotel = await self.owned(owner_id, hotel_id)
        if not self._editor.remove_room(hotel, room_id):
            raise HotelError(NOT_FOUND)
        return hotel

    async def add_photo(self, owner_id: UUID, hotel_id: UUID, data: bytes) -> Any:
        hotel = await self.owned(owner_id, hotel_id)
        images = list(hotel.images or [])
        if len(images) >= MAX_PHOTOS:
            raise HotelError(TOO_MANY_PHOTOS)
        try:
            url = self._photos.save(f"hotel-{hotel.id.hex}", data)
        except PhotoError as exc:
            raise HotelError(BAD_PHOTO) from exc
        hotel.images = [*images, url]
        return hotel

    async def delete_photo(self, owner_id: UUID, hotel_id: UUID, index: int) -> Any:
        hotel = await self.owned(owner_id, hotel_id)
        images = list(hotel.images or [])
        if not 0 <= index < len(images):
            raise HotelError(NOT_FOUND)
        self._photos.delete(images.pop(index))
        hotel.images = images
        return hotel

    @staticmethod
    def _check(draft: HotelDraft) -> None:
        found = problems(draft)
        if found:
            raise HotelError(REJECTED, found)

    @staticmethod
    def _check_room(room: RoomDraft) -> None:
        found = room_problems(room)
        if found:
            raise HotelError(REJECTED, found)
