"""DTO постраничной выдачи."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page[T]:
    """Страница результатов.

    ``page`` — номер страницы, начиная от нуля.
    """

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        """Общее количество страниц (минимум 1)."""
        return max(1, -(-self.total // self.page_size))

    @property
    def has_prev(self) -> bool:
        """Есть ли предыдущая страница."""
        return self.page > 0

    @property
    def has_next(self) -> bool:
        """Есть ли следующая страница."""
        return self.page + 1 < self.pages


def validate_page_params(page: int, page_size: int, max_page_size: int) -> None:
    """Проверяет параметры пагинации.

    Raises:
        ValueError: если номер страницы отрицательный или размер вне диапазона.
    """
    if page < 0:
        raise ValueError("page must be >= 0")
    if not 1 <= page_size <= max_page_size:
        raise ValueError(f"page_size must be in [1, {max_page_size}]")
