from uuid import UUID

import structlog

from bina.application.dtos.pagination import Page, validate_page_params
from bina.application.errors import ListingNotFoundError
from bina.application.repositories.favorites import IFavoritesRepository
from bina.application.repositories.listings import IListingsRepository
from bina.infrastructure.db.models import Listing

logger = structlog.get_logger(__name__)

MAX_PAGE_SIZE = 50


class ToggleFavoriteUseCase:
    """Use-case: добавить объявление в избранное или убрать из него."""

    def __init__(
        self,
        favorites_repository: IFavoritesRepository,
        listings_repository: IListingsRepository,
    ) -> None:
        self.favorites_repository = favorites_repository
        self.listings_repository = listings_repository

    async def execute(self, user_id: UUID, listing_id: UUID) -> bool:
        """Переключает состояние избранного.

        Returns:
            True, если объявление теперь в избранном, иначе False.

        Raises:
            ListingNotFoundError: если добавляется несуществующее или удалённое объявление.
        """
        if await self.favorites_repository.exists(user_id, listing_id):
            await self.favorites_repository.remove(user_id, listing_id)
            logger.info("Favorite removed", user_id=user_id, listing_id=listing_id)
            return False

        listing = await self.listings_repository.get_by_id(listing_id)
        if listing is None or listing.is_deleted:
            raise ListingNotFoundError(listing_id)

        await self.favorites_repository.add(user_id, listing_id)
        logger.info("Favorite added", user_id=user_id, listing_id=listing_id)
        return True


class GetFavoritesUseCase:
    """Use-case: постраничный список избранных объявлений пользователя."""

    def __init__(self, favorites_repository: IFavoritesRepository) -> None:
        self.favorites_repository = favorites_repository

    async def execute(
        self,
        user_id: UUID,
        page: int = 0,
        page_size: int = 5,
    ) -> Page[Listing]:
        """Возвращает страницу избранного.

        Raises:
            ValueError: при некорректных параметрах пагинации.
        """
        validate_page_params(page, page_size, MAX_PAGE_SIZE)

        total = await self.favorites_repository.count_by_user(user_id)
        if total == 0:
            return Page(items=[], total=0, page=page, page_size=page_size)

        items = await self.favorites_repository.list_by_user(
            user_id,
            limit=page_size,
            offset=page * page_size,
        )
        return Page(items=items, total=total, page=page, page_size=page_size)
