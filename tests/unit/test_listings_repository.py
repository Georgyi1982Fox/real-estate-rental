import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.bina.application.repositories.listings import IListingsRepository
from src.bina.infrastructure.db.models import Listing, ListingStatus
from src.bina.infrastructure.db.repositories.listings import ListingsRepository


@pytest.fixture
def session() -> AsyncMock:
    """Фикстура для мокированной сессии."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(session: AsyncMock) -> ListingsRepository:
    """Фикстура для репозитория."""
    return ListingsRepository(session)


def test_repository_implements_interface(repository: ListingsRepository) -> None:
    """Проверка, что репозиторий реализует интерфейс."""
    assert isinstance(repository, IListingsRepository)


@pytest.mark.asyncio
async def test_get_active_listings_by_district(repository: ListingsRepository, session: AsyncMock) -> None:
    """Тест получения активных объявлений по району."""
    from uuid import UUID
    
    # Arrange
    district_id = UUID("12345678-1234-5678-1234-567812345678")
    limit = 10
    
    mock_listing = MagicMock(spec=Listing)
    session.execute.return_value.scalars.return_value.all.return_value = [mock_listing]
    
    # Act
    result = await repository.get_active_listings_by_district(district_id, limit)
    
    # Assert
    assert len(result) == 1
    assert result[0] == mock_listing
    session.execute.assert_called_once()