from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.dtos.pagination import Page, validate_page_params
from bina.application.repositories.listings import IListingsRepository
from bina.infrastructure.db.models import Listing

MAX_PAGE_SIZE = 50


class SearchListingsUseCase:
    """Use-case: постраничный поиск активных объявлений по фильтрам."""

    def __init__(self, listings_repository: IListingsRepository) -> None:
        self.listings_repository = listings_repository

    async def execute(
        self,
        filters: ListingSearchFilters,
        page: int = 0,
        page_size: int = 5,
    ) -> Page[Listing]:
        """Возвращает страницу объявлений и общее количество найденных.

        Raises:
            ValueError: при некорректных параметрах пагинации.
        """
        validate_page_params(page, page_size, MAX_PAGE_SIZE)

        total = await self.listings_repository.count(filters)
        if total == 0:
            return Page(items=[], total=0, page=page, page_size=page_size)

        items = await self.listings_repository.search(
            filters,
            limit=page_size,
            offset=page * page_size,
        )
        return Page(items=items, total=total, page=page, page_size=page_size)
