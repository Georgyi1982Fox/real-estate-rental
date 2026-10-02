"""Переписка с хозяином и просмотры (TASK-111, TASK-112). Не коммитит."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

import structlog

from bina.application.chat import (
    MAX_NEW_CHATS_PER_DAY,
    MAX_PENDING_VIEWINGS,
    REMIND_BEFORE,
    VIEWING_LENGTH,
    ChatError,
    ChatErrorCode,
    ViewingStatus,
    clean_message,
    valid_slot,
)
from bina.application.ports.translator import IMessageTranslator, TranslationError
from bina.infrastructure.db.models import Conversation, Listing, User, Viewing
from bina.infrastructure.db.repositories.chat import ChatRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Delivery:
    """Сообщение для получателя: оригинал и перевод на его язык."""

    conversation: Conversation
    listing: Listing
    sender: User
    recipient: User
    text: str
    translated: str | None
    # Получатель — хозяин (иначе арендатор)
    to_owner: bool


@dataclass(frozen=True, slots=True)
class ViewingNotice:
    """Просмотр и обе стороны — для сообщений в боте."""

    viewing: Viewing
    listing: Listing
    tenant: User
    owner: User


class ChatUseCase:
    def __init__(
        self, repository: ChatRepository, translator: IMessageTranslator | None = None
    ) -> None:
        self._repository = repository
        self._translator = translator

    async def listing_for(self, listing_id: UUID, tenant: User) -> Listing:
        """Квартира хозяина, которому ``tenant`` может написать."""
        listing = await self._repository.owner_listing(listing_id)
        if listing is None:
            raise ChatError(ChatErrorCode.NOT_FOUND)
        if listing.owner_user_id == tenant.id:
            raise ChatError(ChatErrorCode.OWN_LISTING)
        return listing

    async def start(self, listing_id: UUID, tenant: User, now: datetime) -> Conversation:
        """Диалог о квартире (новый или уже начатый)."""
        listing = await self.listing_for(listing_id, tenant)
        existing = await self._repository.conversation_for(listing.id, tenant.id)
        if existing is not None:
            return existing
        since = now - timedelta(days=1)
        if await self._repository.count_conversations_since(tenant.id, since) >= (
            MAX_NEW_CHATS_PER_DAY
        ):
            raise ChatError(ChatErrorCode.LIMIT)
        assert listing.owner_user_id is not None
        return await self._repository.create_conversation(
            listing.id, tenant.id, listing.owner_user_id, now
        )

    async def send(
        self, conversation_id: UUID, sender: User, text: str | None, now: datetime
    ) -> Delivery:
        """Сохраняет сообщение и переводит его на язык получателя."""
        message = clean_message(text)
        conversation = await self._repository.conversation(conversation_id)
        if conversation is None or sender.id not in (conversation.tenant_id, conversation.owner_id):
            raise ChatError(ChatErrorCode.NOT_FOUND)
        to_owner = sender.id == conversation.tenant_id
        recipient_id = conversation.owner_id if to_owner else conversation.tenant_id
        recipient = await self._repository.user(recipient_id)
        listing = await self._repository.listing(conversation.listing_id)
        if recipient is None or listing is None:
            raise ChatError(ChatErrorCode.NOT_FOUND)
        translated = await self._translate(message, sender.language, recipient.language)
        await self._repository.add_message(
            conversation, sender.id, message, translated, recipient.language, now
        )
        return Delivery(conversation, listing, sender, recipient, message, translated, to_owner)

    async def _translate(self, text: str, source: str, target: str) -> str | None:
        if self._translator is None or source == target:
            return None
        try:
            translated = await self._translator.translate_message(text, target)
        except TranslationError as exc:
            # Сообщение всё равно доставим — без перевода
            logger.warning("Chat message not translated", error=str(exc))
            return None
        return translated if translated != text else None

    # --- просмотры

    async def busy_hours(self, listing_id: UUID, day: date) -> set[int]:
        return await self._repository.busy_hours(listing_id, day)

    async def request_viewing(
        self, listing_id: UUID, tenant: User, starts_at: datetime, now: datetime
    ) -> ViewingNotice:
        """Просьба арендатора о просмотре в выбранный час."""
        listing = await self.listing_for(listing_id, tenant)
        if not valid_slot(starts_at, now):
            raise ChatError(ChatErrorCode.SLOT_INVALID)
        if await self._repository.busy_starts(listing.id, starts_at, starts_at + VIEWING_LENGTH):
            raise ChatError(ChatErrorCode.SLOT_TAKEN)
        if await self._repository.count_pending(tenant.id, now) >= MAX_PENDING_VIEWINGS:
            raise ChatError(ChatErrorCode.TOO_MANY_VIEWINGS)
        assert listing.owner_user_id is not None
        owner = await self._repository.user(listing.owner_user_id)
        if owner is None:
            raise ChatError(ChatErrorCode.NOT_FOUND)
        viewing = await self._repository.add_viewing(listing, tenant.id, starts_at, now)
        return ViewingNotice(viewing, listing, tenant, owner)

    async def answer_viewing(
        self, viewing_id: UUID, owner: User, confirm: bool, now: datetime
    ) -> ViewingNotice:
        """Ответ хозяина: «Подходит» или «Другое время»."""
        viewing = await self._repository.viewing(viewing_id)
        if viewing is None or viewing.owner_id != owner.id:
            raise ChatError(ChatErrorCode.NOT_FOUND)
        if viewing.status != ViewingStatus.PENDING:
            raise ChatError(ChatErrorCode.ALREADY_ANSWERED)
        if confirm and await self._repository.busy_starts(
            viewing.listing_id, viewing.starts_at, viewing.starts_at + VIEWING_LENGTH
        ):
            # Хозяин уже подтвердил другого арендатора на это время
            raise ChatError(ChatErrorCode.SLOT_TAKEN)
        if confirm and viewing.starts_at <= now:
            raise ChatError(ChatErrorCode.SLOT_INVALID)
        status = ViewingStatus.CONFIRMED if confirm else ViewingStatus.DECLINED
        await self._repository.set_status(viewing, status, now)
        return await self._notice(viewing)

    async def due_reminders(self, now: datetime) -> list[ViewingNotice]:
        """Подтверждённые просмотры, до которых осталось не больше двух часов."""
        notices = []
        for viewing in await self._repository.due_reminders(now, REMIND_BEFORE):
            try:
                notices.append(await self._notice(viewing))
            except ChatError:
                await self._repository.mark_reminded(viewing, now)
        return notices

    async def mark_reminded(self, viewing: Viewing, now: datetime) -> None:
        await self._repository.mark_reminded(viewing, now)

    async def _notice(self, viewing: Viewing) -> ViewingNotice:
        listing = await self._repository.listing(viewing.listing_id)
        tenant = await self._repository.user(viewing.tenant_id)
        owner = await self._repository.user(viewing.owner_id)
        if listing is None or tenant is None or owner is None:
            raise ChatError(ChatErrorCode.NOT_FOUND)
        return ViewingNotice(viewing, listing, tenant, owner)
