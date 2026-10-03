"""Диалоги с хозяином, сообщения и просмотры (TASK-111, TASK-112)."""

from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bina.application.chat import VIEWING_LENGTH, ViewingStatus, viewing_start
from bina.application.owner_listings import OWNER_SOURCE
from bina.application.rent_reminders import TBILISI
from bina.infrastructure.db.models import (
    ChatMessage,
    Conversation,
    Listing,
    ListingStatus,
    User,
    Viewing,
)


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def owner_listing(self, listing_id: UUID) -> Listing | None:
        """Объявление хозяина в поиске (только с ним можно переписываться)."""
        query = (
            select(Listing)
            .options(selectinload(Listing.district))
            .where(
                Listing.id == listing_id,
                Listing.source_name == OWNER_SOURCE,
                Listing.owner_user_id.is_not(None),
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                # Скрытое модератором или блокировкой агентства — не для переписки
                Listing.hidden_at.is_(None),
            )
        )
        return (await self._session.execute(query)).scalar_one_or_none()

    async def listing(self, listing_id: UUID) -> Listing | None:
        """Объявление в любом статусе (для заголовка в уже начатом диалоге)."""
        query = (
            select(Listing).options(selectinload(Listing.district)).where(Listing.id == listing_id)
        )
        return (await self._session.execute(query)).scalar_one_or_none()

    async def user(self, user_id: UUID) -> User | None:
        query = select(User).where(User.id == user_id, User.is_deleted.is_(False))
        return (await self._session.execute(query)).scalar_one_or_none()

    # --- диалоги

    async def conversation(self, conversation_id: UUID) -> Conversation | None:
        return await self._session.get(Conversation, conversation_id)

    async def conversation_for(self, listing_id: UUID, tenant_id: UUID) -> Conversation | None:
        query = select(Conversation).where(
            Conversation.listing_id == listing_id, Conversation.tenant_id == tenant_id
        )
        return (await self._session.execute(query)).scalar_one_or_none()

    async def count_conversations_since(self, tenant_id: UUID, since: datetime) -> int:
        query = select(func.count()).where(
            Conversation.tenant_id == tenant_id, Conversation.created_at >= since
        )
        return int((await self._session.execute(query)).scalar_one())

    async def create_conversation(
        self, listing_id: UUID, tenant_id: UUID, owner_id: UUID, now: datetime
    ) -> Conversation:
        conversation = Conversation(
            listing_id=listing_id,
            tenant_id=tenant_id,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def add_message(
        self,
        conversation: Conversation,
        sender_id: UUID,
        text: str,
        translated: str | None,
        target_language: str,
        now: datetime,
    ) -> ChatMessage:
        message = ChatMessage(
            conversation_id=conversation.id,
            sender_id=sender_id,
            text=text,
            translated_text=translated,
            target_language=target_language,
            created_at=now,
            updated_at=now,
        )
        conversation.updated_at = now
        self._session.add(message)
        await self._session.flush()
        return message

    async def messages(self, conversation_id: UUID) -> list[ChatMessage]:
        query = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at)
        )
        return list((await self._session.execute(query)).scalars().all())

    # --- просмотры

    async def viewing(self, viewing_id: UUID) -> Viewing | None:
        return await self._session.get(Viewing, viewing_id)

    async def count_pending(self, tenant_id: UUID, now: datetime) -> int:
        query = select(func.count()).where(
            Viewing.tenant_id == tenant_id,
            Viewing.status == ViewingStatus.PENDING,
            Viewing.starts_at > now,
        )
        return int((await self._session.execute(query)).scalar_one())

    async def busy_starts(self, listing_id: UUID, start: datetime, end: datetime) -> list[datetime]:
        """Начала подтверждённых просмотров квартиры в промежутке."""
        query = select(Viewing.starts_at).where(
            Viewing.listing_id == listing_id,
            Viewing.status == ViewingStatus.CONFIRMED,
            Viewing.starts_at > start - VIEWING_LENGTH,
            Viewing.starts_at < end,
        )
        return list((await self._session.execute(query)).scalars().all())

    async def busy_hours(self, listing_id: UUID, day: date) -> set[int]:
        """Часы дня, занятые подтверждёнными просмотрами квартиры."""
        start = viewing_start(day, 0)
        starts = await self.busy_starts(listing_id, start, start + timedelta(days=1))
        local = [value.astimezone(TBILISI) for value in starts]
        return {value.hour for value in local if value.date() == day}

    async def add_viewing(
        self, listing: Listing, tenant_id: UUID, starts_at: datetime, now: datetime
    ) -> Viewing:
        assert listing.owner_user_id is not None
        viewing = Viewing(
            listing_id=listing.id,
            tenant_id=tenant_id,
            owner_id=listing.owner_user_id,
            starts_at=starts_at,
            status=ViewingStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self._session.add(viewing)
        await self._session.flush()
        return viewing

    async def set_status(self, viewing: Viewing, status: ViewingStatus, now: datetime) -> None:
        viewing.status = status
        viewing.updated_at = now
        await self._session.flush()

    async def due_reminders(self, now: datetime, ahead: timedelta) -> list[Viewing]:
        """Подтверждённые просмотры в ближайшие ``ahead``, о которых ещё не напоминали."""
        query = (
            select(Viewing)
            .where(
                Viewing.status == ViewingStatus.CONFIRMED,
                Viewing.reminded_at.is_(None),
                Viewing.starts_at > now,
                Viewing.starts_at <= now + ahead,
            )
            .order_by(Viewing.starts_at)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def mark_reminded(self, viewing: Viewing, now: datetime) -> None:
        viewing.reminded_at = now
        await self._session.flush()
