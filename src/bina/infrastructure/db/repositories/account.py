"""Свои данные пользователя: выгрузка и удаление (TASK-060, TASK-059, GDPR)."""

import secrets
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.owner_listings import OWNER_SOURCE
from bina.infrastructure.db.models import (
    Agency,
    AIUsage,
    ChatMessage,
    Complaint,
    Conversation,
    DocumentSignature,
    Favorite,
    Listing,
    Notification,
    Payment,
    RentReminder,
    SavedSearch,
    SignedDocument,
    User,
    Verification,
    Viewing,
)
from bina.infrastructure.db.models.base import Base
from bina.infrastructure.db.models.users import SubscriptionTier, UserRole

# Служебные поля, которые человеку ничего не говорят
_SKIP = frozenset({"user_id", "updated_at", "is_deleted", "deleted_at", "content", "token"})
_LISTING_FIELDS = (
    "id",
    "title_ru",
    "title_ka",
    "title_en",
    "description_ru",
    "description_ka",
    "description_en",
    "price",
    "currency",
    "rooms",
    "area",
    "floor",
    "address",
    "latitude",
    "longitude",
    "phone",
    "owner_name",
    "images",
    "status",
    "created_at",
)


def _value(value: Any) -> Any:
    """Значение для JSON."""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_value(item) for item in value]
    return value


def _row(item: Base, fields: tuple[str, ...] | None = None) -> dict[str, Any]:
    names = fields or tuple(
        column.key for column in item.__table__.columns if column.key not in _SKIP
    )
    return {name: _value(getattr(item, name)) for name in names}


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _all(
        self, model: type[Base], *conditions: ColumnElement[bool]
    ) -> list[dict[str, Any]]:
        rows = (await self._session.execute(select(model).where(*conditions))).scalars()
        return [_row(row) for row in rows]

    def _own_listings(self, user_id: UUID) -> list[ColumnElement[bool]]:
        return [Listing.owner_user_id == user_id, Listing.source_name == OWNER_SOURCE]

    async def export(self, user: User) -> dict[str, Any]:
        """Всё, что мы храним о человеке, — словарь для JSON-файла."""
        uid = user.id
        listings = (
            (await self._session.execute(select(Listing).where(*self._own_listings(uid))))
            .scalars()
            .all()
        )
        conversations = or_(Conversation.tenant_id == uid, Conversation.owner_id == uid)
        return {
            "profile": {
                "telegram_id": user.telegram_id,
                "language": user.language,
                "registered_at": _value(user.created_at),
                "subscription": _value(user.subscription_tier),
                "subscription_expires_at": _value(user.subscription_expires_at),
                "balance": _value(user.balance),
                "referral_code": user.referral_code,
            },
            "payments": await self._all(Payment, Payment.user_id == uid),
            "favorites": await self._all(Favorite, Favorite.user_id == uid),
            "saved_searches": await self._all(SavedSearch, SavedSearch.user_id == uid),
            "notifications": await self._all(Notification, Notification.user_id == uid),
            "rent_reminders": await self._all(RentReminder, RentReminder.user_id == uid),
            "listings": [_row(listing, _LISTING_FIELDS) for listing in listings],
            "agency": await self._all(Agency, Agency.user_id == uid),
            "conversations": await self._all(Conversation, conversations),
            "messages_sent": await self._all(ChatMessage, ChatMessage.sender_id == uid),
            "viewings": await self._all(
                Viewing, or_(Viewing.tenant_id == uid, Viewing.owner_id == uid)
            ),
            "complaints": await self._all(Complaint, Complaint.user_id == uid),
            "owner_verifications": await self._all(Verification, Verification.user_id == uid),
            "ai_requests_by_day": await self._all(AIUsage, AIUsage.user_id == uid),
            # TASK-115: документы на подпись (без самих файлов — их можно скачать в профиле)
            "documents_created": await self._all(SignedDocument, SignedDocument.creator_id == uid),
            "signatures": await self._all(DocumentSignature, DocumentSignature.user_id == uid),
        }

    async def erase(self, user: User, now: datetime) -> list[str]:
        """Удалить личные данные; вернуть ссылки на фото и логотип, которые надо стереть.

        Платежи остаются (их требует бухгалтерия), но уже ни с кем не связаны: у записи
        пользователя нет Telegram ID и других данных. Если человек снова напишет боту,
        он начнёт с нуля.
        """
        uid = user.id
        files: list[str] = []
        listings = (
            (await self._session.execute(select(Listing).where(*self._own_listings(uid))))
            .scalars()
            .all()
        )
        for listing in listings:
            files.extend(listing.images or [])
            listing.images = []
            listing.phone = None
            listing.owner_name = None
            listing.address = None
            listing.latitude = None
            listing.longitude = None
            listing.url = None
            listing.owner_user_id = None
            listing.is_deleted = True
            listing.deleted_at = now
            listing.hidden_at = listing.hidden_at or now
        agency = (
            await self._session.execute(select(Agency).where(Agency.user_id == uid))
        ).scalar_one_or_none()
        if agency is not None:
            if agency.logo_url:
                files.append(agency.logo_url)
            await self._session.delete(agency)
        # Переписка удаляется целиком (сообщения — каскадом), показы — тоже
        await self._session.execute(
            delete(Conversation).where(
                or_(Conversation.tenant_id == uid, Conversation.owner_id == uid)
            )
        )
        await self._session.execute(
            delete(Viewing).where(or_(Viewing.tenant_id == uid, Viewing.owner_id == uid))
        )
        # TASK-115: свои документы и подписи (вторая сторона уже получила файл в Telegram)
        await self._session.execute(delete(SignedDocument).where(SignedDocument.creator_id == uid))
        for model in (
            DocumentSignature,
            Favorite,
            Notification,
            SavedSearch,
            RentReminder,
            Complaint,
            Verification,
            AIUsage,
        ):
            await self._session.execute(delete(model).where(model.user_id == uid))
        await self._session.execute(
            update(User)
            .where(User.id == uid)
            .values(
                # Отрицательный случайный ID: настоящий Telegram ID больше не хранится,
                # а при новом /start человек получит новую чистую запись
                telegram_id=-(secrets.randbits(62) + 1),
                role=UserRole.USER,
                balance=0,
                subscription_tier=SubscriptionTier.FREE,
                subscription_expires_at=None,
                premium_reminded_for=None,
                premium_expired_notified_for=None,
                referral_code=None,
                referred_by=None,
                is_deleted=True,
                deleted_at=now,
            )
        )
        await self._session.flush()
        return files
