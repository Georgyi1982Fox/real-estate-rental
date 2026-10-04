"""Подборка «Вам может понравиться» (TASK-076)."""

from typing import Protocol
from uuid import UUID

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.recommendations import (
    CANDIDATES,
    RECOMMENDATIONS_LIMIT,
    TASTE_FROM,
    pick,
    taste_of,
)
from bina.infrastructure.db.models import Listing


class IFavorites(Protocol):
    async def list_by_user(self, user_id: UUID, limit: int, offset: int = 0) -> list[Listing]: ...


class IListings(Protocol):
    async def search(self, filters: ListingSearchFilters, limit: int) -> list[Listing]: ...


class IDistrictCities(Protocol):
    async def cities_of(self, district_ids: list[UUID]) -> dict[UUID, str]: ...


class RecommendUseCase:
    def __init__(
        self, favorites: IFavorites, listings: IListings, districts: IDistrictCities
    ) -> None:
        self._favorites = favorites
        self._listings = listings
        self._districts = districts

    async def execute(
        self, user_id: UUID, limit: int = RECOMMENDATIONS_LIMIT
    ) -> tuple[list[Listing], int]:
        """Подборка и сколько избранного учтено (0 — избранного нет, подборки нет)."""
        favorites = await self._favorites.list_by_user(user_id, limit=TASTE_FROM)
        cities = await self._districts.cities_of(list({item.district_id for item in favorites}))
        taste = taste_of(favorites, cities)
        if taste is None:
            return [], 0
        filters = ListingSearchFilters(city=taste.city, rent_period=taste.rent_period)
        candidates = await self._listings.search(filters, limit=CANDIDATES)
        exclude = {item.id for item in favorites}
        return pick(candidates, taste, exclude, limit), len(favorites)
