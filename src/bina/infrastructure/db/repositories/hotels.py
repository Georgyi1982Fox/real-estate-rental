"""Гостиницы (TASK-120): размещение хозяином, поиск, жалобы."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, cast, func, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.complaints import HIDE_AFTER, TRUSTED_ACCOUNT_AGE_HOURS
from bina.application.hotels import HotelDraft, RoomDraft, night_price_gel
from bina.application.localization import dominant_script
from bina.infrastructure.db.models import Hotel, HotelComplaint, HotelRoom, User

# Порядок выдачи (параметр sort)
SORTS = ("newest", "price_asc", "price_desc", "stars_desc")


@dataclass(frozen=True)
class HotelFilters:
    """Фильтры поиска гостиниц; ``None`` / пусто — без фильтра."""

    city: str | None = None
    kinds: tuple[str, ...] = ()
    guests: int | None = None
    price_min: float | None = None
    price_max: float | None = None
    stars_min: int | None = None
    amenities: tuple[str, ...] = ()


def visible() -> list[ColumnElement[bool]]:
    """Условия «объект в поиске»: включён, не скрыт, есть номера с ценой."""
    return [
        Hotel.is_active.is_(True),
        Hotel.hidden_at.is_(None),
        Hotel.min_price_gel.is_not(None),
    ]


class HotelsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ---------------------------------------------------------------- хозяин

    async def create(self, owner_id: UUID, draft: HotelDraft) -> Hotel:
        hotel = Hotel(owner_user_id=owner_id, images=[], amenities=[], fraud_reasons=[])
        apply_draft(hotel, draft)
        hotel.rooms = [room_from_draft(room) for room in draft.rooms]
        refresh_summary(hotel)
        self._session.add(hotel)
        await self._session.flush()
        return hotel

    async def owned(self, owner_id: UUID, hotel_id: UUID) -> Hotel | None:
        hotel = await self._session.get(Hotel, hotel_id)
        return hotel if hotel is not None and hotel.owner_user_id == owner_id else None

    async def list_for_owner(self, owner_id: UUID) -> list[Hotel]:
        query = (
            select(Hotel)
            .where(Hotel.owner_user_id == owner_id)
            .order_by(Hotel.is_active.desc(), Hotel.created_at.desc())
        )
        return list((await self._session.execute(query)).scalars().all())

    async def count_active(self, owner_id: UUID) -> int:
        query = select(func.count()).where(
            Hotel.owner_user_id == owner_id, Hotel.is_active.is_(True)
        )
        return int((await self._session.execute(query)).scalar_one())

    async def count_created_since(self, owner_id: UUID, since: datetime) -> int:
        query = select(func.count()).where(
            Hotel.owner_user_id == owner_id, Hotel.created_at > since
        )
        return int((await self._session.execute(query)).scalar_one())

    async def delete(self, hotel: Hotel) -> None:
        await self._session.delete(hotel)
        await self._session.flush()

    # ---------------------------------------------------------------- поиск

    async def search(
        self, filters: HotelFilters, sort: str, page: int, per_page: int, now: datetime
    ) -> tuple[list[Hotel], int]:
        query = self._filtered(select(Hotel), filters)
        total = int(
            (
                await self._session.execute(
                    self._filtered(select(func.count()).select_from(Hotel), filters)
                )
            ).scalar_one()
        )
        promoted = func.coalesce(Hotel.promoted_until > now, False)
        order: list[Any] = [promoted.desc()]
        if sort == "price_asc":
            order.append(Hotel.min_price_gel.asc())
        elif sort == "price_desc":
            order.append(Hotel.min_price_gel.desc())
        elif sort == "stars_desc":
            order.append(Hotel.stars.desc().nulls_last())
        order.append(Hotel.created_at.desc())
        query = query.order_by(*order).offset((page - 1) * per_page).limit(per_page)
        return list((await self._session.execute(query)).scalars().all()), total

    def _filtered(self, query: Select[Any], filters: HotelFilters) -> Select[Any]:
        conditions = visible()
        if filters.city:
            conditions.append(Hotel.city == filters.city)
        if filters.kinds:
            conditions.append(Hotel.kind.in_(filters.kinds))
        if filters.guests:
            conditions.append(Hotel.max_guests >= filters.guests)
        if filters.price_min is not None:
            conditions.append(Hotel.min_price_gel >= filters.price_min)
        if filters.price_max is not None:
            conditions.append(Hotel.min_price_gel <= filters.price_max)
        if filters.stars_min:
            conditions.append(Hotel.stars >= filters.stars_min)
        for code in filters.amenities:
            # JSON-список удобств содержит код (amenities::jsonb @> '["wifi"]')
            conditions.append(cast(Hotel.amenities, JSONB).contains([code]))
        return query.where(*conditions)

    async def get_visible(self, hotel_id: UUID) -> Hotel | None:
        query = select(Hotel).where(Hotel.id == hotel_id, *visible())
        return (await self._session.execute(query)).scalar_one_or_none()

    # ---------------------------------------------------------------- модерация

    async def hide(self, hotel_id: UUID) -> None:
        await self._session.execute(
            update(Hotel)
            .where(Hotel.id == hotel_id, Hotel.hidden_at.is_(None))
            .values(hidden_at=datetime.now(UTC))
        )

    async def complaints_today(self, user_id: UUID, now: datetime) -> int:
        query = select(func.count()).where(
            HotelComplaint.user_id == user_id,
            HotelComplaint.created_at > now - timedelta(days=1),
        )
        return int((await self._session.execute(query)).scalar_one())

    async def complain(self, hotel_id: UUID, user_id: UUID, reason: str, comment: str) -> bool:
        """Жалоба (как на квартиры); ``True`` — объект скрыт жалобами."""
        now = datetime.now(UTC)
        await self._session.execute(
            insert(HotelComplaint)
            .values(hotel_id=hotel_id, user_id=user_id, reason=reason, comment=comment)
            .on_conflict_do_update(
                index_elements=["hotel_id", "user_id"],
                set_={"reason": reason, "comment": comment, "created_at": now},
                where=HotelComplaint.resolved_at.is_(None),
            )
        )
        trusted_since = now - timedelta(hours=TRUSTED_ACCOUNT_AGE_HOURS)
        open_count = (
            await self._session.execute(
                select(func.count())
                .select_from(HotelComplaint)
                .join(User, User.id == HotelComplaint.user_id)
                .where(
                    HotelComplaint.hotel_id == hotel_id,
                    HotelComplaint.resolved_at.is_(None),
                    User.created_at <= trusted_since,
                )
            )
        ).scalar_one()
        if open_count < HIDE_AFTER:
            return False
        # Оплаченные и проверенные сами не скрываются — решает модератор
        result = await self._session.execute(
            update(Hotel)
            .where(
                Hotel.id == hotel_id,
                Hotel.hidden_at.is_(None),
                Hotel.is_verified.is_not(True),
                or_(Hotel.promoted_until.is_(None), Hotel.promoted_until <= now),
            )
            .values(hidden_at=now)
            .returning(Hotel.id)
        )
        return result.first() is not None


def apply_draft(hotel: Hotel, draft: HotelDraft) -> None:
    """Поля объекта из черновика (кроме номеров и фото)."""
    hotel.kind = draft.kind
    hotel.name = draft.name.strip()
    hotel.city = draft.city
    hotel.address = draft.address
    hotel.latitude = draft.latitude
    hotel.longitude = draft.longitude
    hotel.stars = draft.stars
    hotel.amenities = list(draft.amenities)
    hotel.check_in = draft.check_in
    hotel.check_out = draft.check_out
    hotel.phone = draft.phone
    hotel.whatsapp = draft.whatsapp
    hotel.contact_url = draft.contact_url
    set_description(hotel, draft.description)


def set_description(hotel: Hotel, description: str) -> None:
    """Описание — в колонку своего языка; старые переводы сбрасываются."""
    text = description.strip()
    language = dominant_script(text) or "en"
    for code in ("ka", "ru", "en"):
        setattr(hotel, f"description_{code}", text if code == language else "")


def room_from_draft(room: RoomDraft) -> HotelRoom:
    return HotelRoom(
        kind=room.kind,
        title=room.title.strip(),
        guests=room.guests,
        price=Decimal(str(room.price)),
        currency=room.currency,
        count=room.count,
    )


def refresh_summary(hotel: Hotel) -> None:
    """Цена «от» в лари и вместимость — для поиска и сортировки."""
    rooms = list(hotel.rooms)
    if not rooms:
        hotel.min_price_gel = None
        hotel.max_guests = 0
        return
    cheapest = min(night_price_gel(float(room.price), room.currency) for room in rooms)
    hotel.min_price_gel = Decimal(str(round(cheapest, 2)))
    hotel.max_guests = max(room.guests for room in rooms)


class HotelEditor:
    """Изменение загруженного объекта: поля, номера (цена «от» пересчитывается)."""

    def apply(self, hotel: Hotel, draft: HotelDraft) -> None:
        apply_draft(hotel, draft)

    def add_room(self, hotel: Hotel, room: RoomDraft) -> HotelRoom:
        new = room_from_draft(room)
        hotel.rooms.append(new)
        refresh_summary(hotel)
        return new

    def update_room(self, hotel: Hotel, room_id: UUID, room: RoomDraft) -> bool:
        for existing in hotel.rooms:
            if existing.id == room_id:
                updated = room_from_draft(room)
                existing.kind = updated.kind
                existing.title = updated.title
                existing.guests = updated.guests
                existing.price = updated.price
                existing.currency = updated.currency
                existing.count = updated.count
                refresh_summary(hotel)
                return True
        return False

    def remove_room(self, hotel: Hotel, room_id: UUID) -> bool:
        for existing in list(hotel.rooms):
            if existing.id == room_id:
                hotel.rooms.remove(existing)
                refresh_summary(hotel)
                return True
        return False
