"""Перевод описаний гостиниц на недостающие языки (TASK-120, этап 2).

Хозяин вводит описание гостиницы на одном языке (его колонка ``description_*``
заполняется при размещении), остальные языковые колонки пусты. Use case находит
такие гостиницы и переводит описание на недостающие языки отдельными сообщениями
(:class:`IMessageTranslator`, как чат с хозяином). У гостиницы нет заголовка —
переводится только описание. Ошибка на одной гостинице не останавливает остальные.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import structlog

from bina.application.ports.translator import LANGUAGES, IMessageTranslator, TranslationError
from bina.infrastructure.db.models import Hotel

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class HotelTranslationStats:
    """Итог запуска."""

    checked: int
    translated: int
    failed: int


class IHotelTranslations(Protocol):
    """Гостиницы без перевода описания и сохранение переводов."""

    async def list_untranslated(self, limit: int) -> list[Hotel]: ...
    async def save_descriptions(self, hotel_id: UUID, by_language: dict[str, str]) -> None: ...


def hotel_description(hotel: Hotel, language: str) -> str:
    """Описание гостиницы на языке ``language`` (пустая строка, если его нет)."""
    return (getattr(hotel, f"description_{language}", None) or "").strip()


def description_language(hotel: Hotel) -> str | None:
    """Язык, на котором введено описание (первый непустой из ru, ka, en)."""
    return next((lang for lang in LANGUAGES if hotel_description(hotel, lang)), None)


def missing_languages(hotel: Hotel) -> list[str]:
    """Языки, на которых описания ещё нет."""
    return [lang for lang in LANGUAGES if not hotel_description(hotel, lang)]


class TranslateHotelsUseCase:
    """Переводит описания до ``limit`` гостиниц за запуск."""

    def __init__(
        self,
        translator: IMessageTranslator,
        repository: IHotelTranslations,
        after_save: Callable[[], Awaitable[None]] | None = None,
        concurrency: int = 1,
    ) -> None:
        self._translator = translator
        self._repository = repository
        self._after_save = after_save
        self._concurrency = max(1, concurrency)

    async def execute(self, limit: int) -> HotelTranslationStats:
        """Находит гостиницы без перевода описания и переводит их.

        Сам не коммитит: транзакцией управляет вызывающий код (см. ``after_save``).
        """
        hotels = await self._repository.list_untranslated(limit)
        translated = failed = 0
        jobs = [
            (hotel, source, targets)
            for hotel in hotels
            if (source := description_language(hotel)) is not None
            and (targets := missing_languages(hotel))
        ]
        semaphore = asyncio.Semaphore(self._concurrency)

        async def run(
            hotel: Hotel, source: str, targets: list[str]
        ) -> tuple[Hotel, dict[str, str] | TranslationError]:
            text = hotel_description(hotel, source)
            async with semaphore:
                try:
                    return hotel, {
                        target: await self._translator.translate_message(text, target)
                        for target in targets
                    }
                except TranslationError as exc:
                    return hotel, exc

        for finished in asyncio.as_completed([run(*job) for job in jobs]):
            hotel, result = await finished
            if isinstance(result, TranslationError):
                failed += 1
                logger.warning(
                    "Hotel translation failed", hotel_id=str(hotel.id), error=str(result)
                )
                continue
            await self._repository.save_descriptions(hotel.id, result)
            if self._after_save is not None:
                await self._after_save()
            translated += 1
            logger.debug("Hotel translated", hotel_id=str(hotel.id), targets=list(result))

        logger.info(
            "Hotel translation finished", checked=len(hotels), translated=translated, failed=failed
        )
        return HotelTranslationStats(checked=len(hotels), translated=translated, failed=failed)
