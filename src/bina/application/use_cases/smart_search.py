"""Умный поиск по смыслу (TASK-012)."""

from typing import Protocol

from bina.application.dtos.listing_search import ListingSearchFilters
from bina.application.dtos.pagination import Page, validate_page_params
from bina.application.ports.embeddings import IEmbedder
from bina.application.semantic_search import SMART_LIMIT
from bina.application.use_cases.search_listings import MAX_PAGE_SIZE
from bina.infrastructure.db.models import Listing


class ISemanticSearchRepository(Protocol):
    async def semantic_search(
        self,
        filters: ListingSearchFilters,
        vector: list[float],
        model: str,
        limit: int,
        offset: int = 0,
    ) -> list[Listing]: ...

    async def semantic_count(self, filters: ListingSearchFilters, model: str) -> int: ...


class SmartSearchUseCase:
    """Объявления, самые близкие по смыслу к ``filters.query``, с остальными фильтрами.

    Текст запроса не требует совпадения слов (полнотекстовое условие снимается).
    Показываются первые ``SMART_LIMIT`` самых близких.
    """

    def __init__(self, repository: ISemanticSearchRepository, embedder: IEmbedder) -> None:
        self._repository = repository
        self._embedder = embedder

    async def execute(
        self, filters: ListingSearchFilters, page: int = 0, page_size: int = 5
    ) -> Page[Listing]:
        """Raises:
        EmbeddingsError: сервис не ответил (вызывающий переходит на обычный поиск).
        ValueError: некорректная пагинация.
        """
        validate_page_params(page, page_size, MAX_PAGE_SIZE)
        [vector] = await self._embedder.embed([filters.query or ""])
        rest = filters.model_copy(update={"query": None})
        model = self._embedder.model
        total = min(await self._repository.semantic_count(rest, model), SMART_LIMIT)
        offset = page * page_size
        if offset >= total:
            return Page(items=[], total=total, page=page, page_size=page_size)
        items = await self._repository.semantic_search(
            rest, vector, model, limit=min(page_size, total - offset), offset=offset
        )
        return Page(items=items, total=total, page=page, page_size=page_size)
