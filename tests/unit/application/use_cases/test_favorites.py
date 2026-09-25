from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.bina.application.errors import ListingNotFoundError
from src.bina.application.use_cases.favorites import (
    GetFavoritesUseCase,
    ToggleFavoriteUseCase,
)
from src.bina.infrastructure.db.models import Listing


@pytest.fixture
def favorites_repository() -> AsyncMock:
    """Мок репозитория избранного."""
    return AsyncMock()


@pytest.fixture
def listings_repository() -> AsyncMock:
    """Мок репозитория объявлений."""
    return AsyncMock()


@pytest.fixture
def toggle(
    favorites_repository: AsyncMock,
    listings_repository: AsyncMock,
) -> ToggleFavoriteUseCase:
    """Use-case переключения избранного."""
    return ToggleFavoriteUseCase(favorites_repository, listings_repository)


async def test_toggle_adds_when_absent(
    toggle: ToggleFavoriteUseCase,
    favorites_repository: AsyncMock,
    listings_repository: AsyncMock,
) -> None:
    """Отсутствующее объявление добавляется в избранное."""
    user_id, listing_id = uuid4(), uuid4()
    favorites_repository.exists.return_value = False
    listings_repository.get_by_id.return_value = MagicMock(spec=Listing, is_deleted=False)

    assert await toggle.execute(user_id, listing_id) is True
    favorites_repository.add.assert_awaited_once_with(user_id, listing_id)
    favorites_repository.remove.assert_not_awaited()


async def test_toggle_removes_when_present(
    toggle: ToggleFavoriteUseCase,
    favorites_repository: AsyncMock,
    listings_repository: AsyncMock,
) -> None:
    """Уже избранное объявление удаляется, даже если объявление удалено."""
    user_id, listing_id = uuid4(), uuid4()
    favorites_repository.exists.return_value = True

    assert await toggle.execute(user_id, listing_id) is False
    favorites_repository.remove.assert_awaited_once_with(user_id, listing_id)
    favorites_repository.add.assert_not_awaited()
    listings_repository.get_by_id.assert_not_awaited()


@pytest.mark.parametrize("listing", [None, MagicMock(spec=Listing, is_deleted=True)])
async def test_toggle_rejects_missing_listing(
    toggle: ToggleFavoriteUseCase,
    favorites_repository: AsyncMock,
    listings_repository: AsyncMock,
    listing: Listing | None,
) -> None:
    """Нельзя добавить несуществующее или удалённое объявление."""
    listing_id = uuid4()
    favorites_repository.exists.return_value = False
    listings_repository.get_by_id.return_value = listing

    with pytest.raises(ListingNotFoundError) as exc_info:
        await toggle.execute(uuid4(), listing_id)

    assert exc_info.value.listing_id == listing_id
    favorites_repository.add.assert_not_awaited()


async def test_get_favorites_page(favorites_repository: AsyncMock) -> None:
    """Избранное возвращается постранично."""
    user_id = uuid4()
    items = [MagicMock(spec=Listing)]
    favorites_repository.count_by_user.return_value = 6
    favorites_repository.list_by_user.return_value = items

    page = await GetFavoritesUseCase(favorites_repository).execute(user_id, page=1, page_size=5)

    favorites_repository.list_by_user.assert_awaited_once_with(user_id, limit=5, offset=5)
    assert page.items == items
    assert page.pages == 2
    assert page.has_next is False


async def test_get_favorites_empty(favorites_repository: AsyncMock) -> None:
    """Пустое избранное не делает лишний запрос."""
    favorites_repository.count_by_user.return_value = 0

    page = await GetFavoritesUseCase(favorites_repository).execute(uuid4())

    assert page.items == []
    favorites_repository.list_by_user.assert_not_awaited()
