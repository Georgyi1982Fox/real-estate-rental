"""Порт переводчика объявлений (TASK-010)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

# Языки объявлений: поля title_* / description_* модели Listing
LANGUAGES: tuple[str, ...] = ("ru", "ka", "en")


@dataclass(frozen=True, slots=True)
class ListingText:
    """Заголовок и описание объявления на одном языке."""

    title: str
    description: str = ""


class TranslationError(Exception):
    """Переводчик не смог вернуть корректный перевод."""


class ITranslator(ABC):
    """Переводит текст объявления на другие языки."""

    @abstractmethod
    async def translate(
        self,
        text: ListingText,
        source: str,
        targets: Sequence[str],
    ) -> dict[str, ListingText]:
        """Перевод ``text`` с языка ``source`` на каждый из ``targets``.

        Raises:
            TranslationError: если перевод получить не удалось.
        """
