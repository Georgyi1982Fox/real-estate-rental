"""Перевод объявлений на недостающие языки (TASK-010).

Парсеры сохраняют текст на одном языке (MyHome и SS.ge — русский). Use case
находит объявления с пустыми полями других языков и заполняет их переводом.
Ошибка на одном объявлении не останавливает остальные.
"""

from dataclasses import dataclass

import structlog

from bina.application.ports.translator import (
    LANGUAGES,
    ITranslator,
    ListingText,
    TranslationError,
)
from bina.application.repositories.translations import IListingTranslationsRepository
from bina.infrastructure.db.models import Listing

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TranslationStats:
    """Итог запуска."""

    checked: int
    translated: int
    failed: int


def listing_text(listing: Listing, language: str) -> ListingText:
    """Текст объявления на языке ``language`` (пустые строки, если его нет)."""
    return ListingText(
        title=(getattr(listing, f"title_{language}", None) or "").strip(),
        description=(getattr(listing, f"description_{language}", None) or "").strip(),
    )


def source_language(listing: Listing) -> str | None:
    """Язык, с которого переводить: первый из ru, ka, en с непустым заголовком."""
    for language in LANGUAGES:
        if listing_text(listing, language).title:
            return language
    return None


def missing_languages(listing: Listing) -> list[str]:
    """Языки с пустым заголовком."""
    return [language for language in LANGUAGES if not listing_text(listing, language).title]


class TranslateListingsUseCase:
    """Переводит до ``limit`` объявлений за запуск."""

    def __init__(
        self,
        translator: ITranslator,
        repository: IListingTranslationsRepository,
    ) -> None:
        self._translator = translator
        self._repository = repository

    async def execute(self, limit: int) -> TranslationStats:
        """Находит объявления без перевода и переводит их.

        Не коммитит: транзакцией управляет вызывающий код.
        """
        listings = await self._repository.list_untranslated(limit)
        translated = failed = 0
        for listing in listings:
            source = source_language(listing)
            targets = missing_languages(listing)
            if source is None or not targets:
                continue
            try:
                texts = await self._translator.translate(
                    listing_text(listing, source), source, targets
                )
            except TranslationError as exc:
                failed += 1
                logger.warning(
                    "Listing translation failed", listing_id=str(listing.id), error=str(exc)
                )
                continue
            await self._repository.save_texts(listing.id, texts)
            translated += 1
            logger.debug(
                "Listing translated", listing_id=str(listing.id), source=source, targets=targets
            )

        logger.info(
            "Translation finished", checked=len(listings), translated=translated, failed=failed
        )
        return TranslationStats(checked=len(listings), translated=translated, failed=failed)
