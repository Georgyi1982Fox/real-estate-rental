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


class TranslatorUnavailable(TranslationError):
    """AI не отвечает вообще (нет связи, кончился баланс, неверный ключ).

    Объявление тут ни при чём: его не откладываем, а владельцу сообщаем о сбое.
    """


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


class IMessageTranslator(ABC):
    """Переводит сообщения чата арендатора и хозяина (TASK-111)."""

    @abstractmethod
    async def translate_message(self, text: str, target: str) -> str:
        """Перевод ``text`` (язык определяется сам) на ``target``.

        Raises:
            TranslationError: если перевод получить не удалось.
        """
