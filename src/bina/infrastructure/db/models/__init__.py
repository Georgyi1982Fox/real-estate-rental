"""Модули для работы с моделями БД."""

from .agencies import Agency, ListingStat
from .ai_usage import AIUsage
from .base import Base, SoftDeleteMixin, TimestampMixin
from .chat import ChatMessage, Conversation, Viewing
from .complaints import Complaint
from .daily_reports import DailyReportRecord
from .districts import District
from .documents import DocumentSignature, SignedDocument
from .embeddings import Embedding
from .favorites import Favorite
from .listings import Listing, ListingStatus
from .notifications import Notification, NotificationType, SavedSearch
from .payments import Payment
from .photo_reports import PhotoReportRecord
from .rent_reminders import RentReminder
from .scrape_skips import ScrapeSkip
from .users import User
from .verifications import Verification
from .view_history import ViewedListing

__all__ = [
    "AIUsage",
    "Agency",
    "Base",
    "ChatMessage",
    "Complaint",
    "Conversation",
    "DailyReportRecord",
    "District",
    "DocumentSignature",
    "Embedding",
    "Favorite",
    "Listing",
    "ListingStat",
    "ListingStatus",
    "Notification",
    "NotificationType",
    "Payment",
    "PhotoReportRecord",
    "RentReminder",
    "SavedSearch",
    "ScrapeSkip",
    "SignedDocument",
    "SoftDeleteMixin",
    "TimestampMixin",
    "User",
    "Verification",
    "ViewedListing",
    "Viewing",
]
