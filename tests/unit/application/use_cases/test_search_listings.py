from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.use_cases.search_listings import SearchListingsUseCase
from bina.infrastructure.db.models import Listing


@pytest.fixture
def listings_repository() -> AsyncMock:
    """Мок репозитория объявлений."""
    return AsyncMock()


async def test_returns_page_with_offset(listings_repository: AsyncMock) -> None:
    """Смещение считается из номера страницы и размера."""
    filters = ListingSearchFilters(price_max=Decimal("1500"), rooms_min=2)
    items = [MagicMock(spec=Listing), MagicMock(spec=Listing)]
    listings_repository.count.return_value = 12
    listings_repository.search.return_value = items

    page = await SearchListingsUseCase(listings_repository).execute(filters, page=2, page_size=5)

    listings_repository.search.assert_awaited_once_with(filters, limit=5, offset=10)
    assert page.items == items
    assert page.total == 12
    assert page.pages == 3
    assert page.has_prev is True
    assert page.has_next is False


async def test_empty_result_skips_search(listings_repository: AsyncMock) -> None:
    """Если ничего не найдено, выборка не запрашивается."""
    listings_repository.count.return_value = 0

    page = await SearchListingsUseCase(listings_repository).execute(ListingSearchFilters())

    assert page.items == []
    assert page.total == 0
    assert page.pages == 1
    assert page.has_next is False
    listings_repository.search.assert_not_awaited()


@pytest.mark.parametrize(("page", "page_size"), [(-1, 5), (0, 0), (0, 51)])
async def test_invalid_pagination(
    listings_repository: AsyncMock,
    page: int,
    page_size: int,
) -> None:
    """Некорректная пагинация отклоняется до запроса в БД."""
    with pytest.raises(ValueError):
        await SearchListingsUseCase(listings_repository).execute(
            ListingSearchFilters(),
            page=page,
            page_size=page_size,
        )
    listings_repository.count.assert_not_awaited()
