"""Порт хранилища переводов объявлений (TASK-010)."""

from typing import Protocol
from uuid import UUID

from bina.application.ports.translator import ListingText
from bina.infrastructure.db.models import Listing


class IListingTranslationsRepository(Protocol):
    """Объявления без перевода и сохранение переводов."""

    async def list_untranslated(self, limit: int) -> list[Listing]:
        """Активные объявления, у которых пуст заголовок хотя бы на одном языке (новые сверху)."""
        ...

    async def save_texts(self, listing_id: UUID, texts: dict[str, ListingText]) -> None:
        """Записать заголовок и описание для каждого языка из ``texts``."""
        ...
