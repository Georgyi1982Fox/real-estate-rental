"""Перевод на лету (TASK-010): описание всегда на языке того, кто открыл объявление.

Фоновый шаг переводит новые объявления раз в час, но может отставать (много объявлений,
сбой AI). Когда человек открывает квартиру, а описания на его языке ещё нет, переводим её
прямо сейчас (все недостающие языки одним запросом), сохраняем и отдаём уже с переводом.
Не успели за ``TIMEOUT`` или AI не ответил — отдаём как есть, переведёт фоновый шаг.
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.translator import ITranslator, TranslationError
from bina.application.use_cases.translate_listings import (
    TranslateListingsUseCase,
    listing_text,
    missing_languages,
)
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository

logger = structlog.get_logger(__name__)

LANGUAGES = ("ka", "ru", "en")
# Дольше ждать человек не станет: дальше — фоновый перевод
TIMEOUT = 25
# Неудачный перевод не повторяем на каждом открытии
RETRY_AFTER = timedelta(hours=1)


def request_language(request: Request, user_language: str | None) -> str | None:
    """Язык зрителя: из профиля, ``?lang=`` или заголовка браузера ``Accept-Language``."""
    if user_language in LANGUAGES:
        return user_language
    explicit = request.query_params.get("lang")
    if explicit in LANGUAGES:
        return explicit
    for part in request.headers.get("accept-language", "").split(","):
        code = part.strip()[:2].lower()
        if code in LANGUAGES:
            return code
    return None


def translator(request: Request) -> ITranslator | None:
    """Переводчик (в тестах — ``app.state.translator``); без ключа AI — ``None``."""
    injected: ITranslator | None = getattr(request.app.state, "translator", None)
    if injected is not None:
        return injected
    if not os.getenv("LLM_API_KEY"):
        return None
    from bina.infrastructure.llm.llm_factory import LLMFactory
    from bina.infrastructure.llm.translator import LLMTranslator

    created = LLMTranslator(LLMFactory.create_provider())
    request.app.state.translator = created
    return created


def needs_translation(listing: Listing, language: str) -> bool:
    """Нет описания (или заголовка) на языке зрителя, а на другом языке есть."""
    if language not in missing_languages(listing):
        return False
    failed = listing.translation_failed_at
    return failed is None or failed < datetime.now(UTC) - RETRY_AFTER


async def translate_if_missing(
    request: Request, session: AsyncSession, listing: Listing, language: str | None
) -> None:
    """Перевести объявление сейчас, если на языке зрителя текста нет."""
    if language is None or not needs_translation(listing, language):
        return
    active = translator(request)
    if active is None:
        return
    use_case = TranslateListingsUseCase(
        active, ListingsRepository(session), after_save=session.commit
    )
    try:
        await asyncio.wait_for(use_case.translate_one(listing), TIMEOUT)
    except (TimeoutError, TranslationError) as exc:
        logger.info("On-demand translation skipped", listing_id=str(listing.id), error=str(exc))
        return
    await session.refresh(listing)
    logger.info(
        "Listing translated on demand",
        listing_id=str(listing.id),
        language=language,
        has_text=bool(listing_text(listing, language).description),
    )
