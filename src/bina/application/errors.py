"""Ошибки прикладного слоя."""

from uuid import UUID


class ApplicationError(Exception):
    """Базовая ошибка прикладного слоя."""


class ListingNotFoundError(ApplicationError):
    """Объявление не найдено или недоступно."""

    def __init__(self, listing_id: UUID) -> None:
        super().__init__(f"Listing {listing_id} not found")
        self.listing_id = listing_id
