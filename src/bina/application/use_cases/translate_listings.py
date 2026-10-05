"""Перевод объявлений на недостающие языки (TASK-010).

Парсеры сохраняют текст на одном языке (MyHome и SS.ge — русский). Use case
находит объявления с пустыми полями других языков и заполняет их переводом.
Ошибка на одном объявлении не останавливает остальные.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog

from bina.application.ports.translator import (
    LANGUAGES,
    ITranslator,
    ListingText,
    TranslationError,
    TranslatorUnavailable,
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
    # AI не отвечал вовсе (нет связи, баланс, ключ) — объявления не откладывались
    unavailable: int = 0
    error: str = ""


def listing_text(listing: Listing, language: str) -> ListingText:
    """Текст объявления на языке ``language`` (пустые строки, если его нет)."""
    return ListingText(
        title=(getattr(listing, f"title_{language}", None) or "").strip(),
        description=(getattr(listing, f"description_{language}", None) or "").strip(),
    )


def title_language(listing: Listing) -> str | None:
    """Первый из ru, ka, en с непустым заголовком."""
    for language in LANGUAGES:
        if listing_text(listing, language).title:
            return language
    return None


def description_language(listing: Listing) -> str | None:
    """Язык описания: там же, где заголовок, иначе первый с непустым описанием."""
    title_lang = title_language(listing)
    if title_lang is not None and listing_text(listing, title_lang).description:
        return title_lang
    for language in LANGUAGES:
        if listing_text(listing, language).description:
            return language
    return None


def source_language(listing: Listing) -> str | None:
    """Язык, на котором у объявления больше всего текста (для проверки на мошенничество)."""
    return description_language(listing) or title_language(listing)


def missing_languages(listing: Listing) -> list[str]:
    """Языки без заголовка или без описания (если описание вообще есть)."""
    has_description = description_language(listing) is not None
    return [
        language
        for language in LANGUAGES
        if not listing_text(listing, language).title
        or (has_description and not listing_text(listing, language).description)
    ]


class TranslateListingsUseCase:
    """Переводит до ``limit`` объявлений за запуск."""

    def __init__(
        self,
        translator: ITranslator,
        repository: IListingTranslationsRepository,
        after_save: Callable[[], Awaitable[None]] | None = None,
        concurrency: int = 1,
    ) -> None:
        """``after_save`` вызывается после каждого сохранённого перевода (обычно commit).

        Перевод одного объявления идёт секунды: без промежуточного commit строки
        остаются заблокированными на всё время пачки и мешают парсеру.

        ``concurrency`` — сколько объявлений переводится одновременно (запросы к AI
        идут параллельно, сохранение в БД — по одному).
        """
        self._translator = translator
        self._repository = repository
        self._after_save = after_save
        self._concurrency = max(1, concurrency)

    async def execute(self, limit: int) -> TranslationStats:
        """Находит объявления без перевода и переводит их.

        Сам не коммитит: транзакцией управляет вызывающий код (см. ``after_save``).
        """
        listings = await self._repository.list_untranslated(limit)
        translated = failed = unavailable = 0
        error = ""
        jobs = [
            (listing, source, targets)
            for listing in listings
            if (source := title_language(listing)) is not None
            and (targets := missing_languages(listing))
        ]
        semaphore = asyncio.Semaphore(self._concurrency)

        async def run(
            listing: Listing, source: str, targets: list[str]
        ) -> tuple[Listing, str, list[str], dict[str, ListingText] | TranslationError]:
            async with semaphore:
                try:
                    return listing, source, targets, await self._translate(listing, source, targets)
                except TranslationError as exc:
                    return listing, source, targets, exc

        # Сохраняем по мере готовности, по одному: сессия БД не для параллельной работы
        for finished in asyncio.as_completed([run(*job) for job in jobs]):
            listing, source, targets, result = await finished
            if isinstance(result, TranslatorUnavailable):
                # Сбой AI, а не объявления: не откладываем, попробуем в следующий запуск
                failed += 1
                unavailable += 1
                error = str(result)
                logger.warning("Translator unavailable", error=error)
                continue
            if isinstance(result, TranslationError):
                failed += 1
                logger.warning(
                    "Listing translation failed", listing_id=str(listing.id), error=str(result)
                )
                await self._repository.mark_translation_failed(listing.id)
                if self._after_save is not None:
                    await self._after_save()
                continue
            texts = result
            await self._repository.save_texts(listing.id, texts)
            if self._after_save is not None:
                await self._after_save()
            translated += 1
            logger.debug(
                "Listing translated", listing_id=str(listing.id), source=source, targets=targets
            )

        logger.info(
            "Translation finished", checked=len(listings), translated=translated, failed=failed
        )
        return TranslationStats(
            checked=len(listings),
            translated=translated,
            failed=failed,
            unavailable=unavailable,
            error=error,
        )

    async def translate_one(self, listing: Listing) -> bool:
        """Перевести одно объявление сразу (его открыли, а перевода на язык нет).

        ``True`` — перевод сохранён. Ошибки — :class:`TranslationError` (неудачный перевод
        откладывается, как в фоновом шаге).
        """
        source = title_language(listing)
        targets = missing_languages(listing)
        if source is None or not targets:
            return False
        try:
            texts = await self._translate(listing, source, targets)
        except TranslatorUnavailable:
            raise
        except TranslationError:
            await self._repository.mark_translation_failed(listing.id)
            if self._after_save is not None:
                await self._after_save()
            raise
        await self._repository.save_texts(listing.id, texts)
        if self._after_save is not None:
            await self._after_save()
        return True

    async def _translate(
        self, listing: Listing, title_lang: str, targets: list[str]
    ) -> dict[str, ListingText]:
        """Переводы на ``targets``; сохраняются только в пустые поля (``save_texts``).

        Заголовок и описание бывают на разных языках (русский заголовок сайта и
        грузинское описание хозяина). Тогда сначала заголовок переводится на язык
        описания, и дальше всё переводится с языка описания.
        """
        desc_lang = description_language(listing)
        if desc_lang is None or desc_lang == title_lang:
            return await self._translator.translate(
                listing_text(listing, title_lang), title_lang, targets
            )
        title = listing_text(listing, desc_lang).title
        if not title:
            only_title = ListingText(listing_text(listing, title_lang).title)
            first = await self._translator.translate(only_title, title_lang, [desc_lang])
            title = first[desc_lang].title
        source = ListingText(title, listing_text(listing, desc_lang).description)
        texts = await self._translator.translate(
            source, desc_lang, [code for code in targets if code != desc_lang]
        )
        texts[desc_lang] = ListingText(title, source.description)
        return texts
