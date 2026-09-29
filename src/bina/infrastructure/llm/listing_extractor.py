"""AI-разбор объявления из текста поста через LLM (AITUNNEL) — TASK-091.

Как проверка на мошенничество: обычный ``complete``, JSON в ответе, проверка
Pydantic, при кривом ответе — ещё попытка с уточнением.
"""

import json
import re

import httpx
import structlog
from pydantic import BaseModel, ValidationError, field_validator

from bina.application.listing_details import clean_features
from bina.application.ports.listing_extractor import (
    ExtractedListing,
    IListingExtractor,
    ListingExtractionError,
)
from bina.application.ports.llm_provider import LLMProvider
from bina.infrastructure.llm.prompts.extract_listing import build_extract_prompt

logger = structlog.get_logger(__name__)

JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


_NUMBER_RE = re.compile(r"\d[\d\s.,]*")
_THOUSANDS_RE = re.compile(r"\d{1,3}(?:[.,]\d{3})+")


def parse_number(text: str) -> float | None:
    """Первое число в строке: «1 200$» → 1200, «85 м2» → 85, «80.000» → 80000, «65,5» → 65.5."""
    match = _NUMBER_RE.search(text)
    if match is None:
        return None
    number = re.sub(r"\s", "", match.group(0)).rstrip(".,")
    if _THOUSANDS_RE.fullmatch(number):
        number = re.sub(r"[.,]", "", number)
    return float(number.replace(",", "."))


class _Extracted(BaseModel):
    is_rental_offer: bool
    city: str | None = None
    district: str | None = None
    price: float | None = None
    currency: str | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    area: float | None = None
    floor: int | None = None
    total_floors: int | None = None
    address: str | None = None
    phone: str | None = None
    features: list[str] | None = None
    title: str | None = None

    @field_validator("price", "area", mode="before")
    @classmethod
    def _number(cls, value: object) -> object:
        # «800$», «1 200», «85 м2», «80.000$» — модель иногда отдаёт строкой
        return parse_number(value) if isinstance(value, str) else value


def parse_extracted(raw: str) -> ExtractedListing:
    """Разбирает ответ модели; ``ValueError``, если это не нужный JSON."""
    match = JSON_OBJECT_RE.search(raw)
    if match is None:
        raise ValueError("no JSON object in the response")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    try:
        item = _Extracted.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid listing: {exc}") from exc
    currency = (item.currency or "").strip().upper() or None
    return ExtractedListing(
        is_rental_offer=item.is_rental_offer,
        city=(item.city or "").strip() or None,
        district=(item.district or "").strip() or None,
        price=item.price if item.price and item.price > 0 else None,
        currency=currency,
        rooms=item.rooms if item.rooms and item.rooms > 0 else None,
        bedrooms=item.bedrooms if item.bedrooms and item.bedrooms > 0 else None,
        area=item.area if item.area and item.area > 0 else None,
        floor=item.floor,
        total_floors=item.total_floors if item.total_floors and item.total_floors > 0 else None,
        address=(item.address or "").strip() or None,
        phone=(item.phone or "").strip() or None,
        features=clean_features(item.features or []),
        title=(item.title or "").strip() or None,
    )


class LLMListingExtractor(IListingExtractor):
    """:class:`IListingExtractor` поверх :class:`LLMProvider`."""

    def __init__(self, provider: LLMProvider, attempts: int = 2) -> None:
        self._provider = provider
        self._attempts = attempts

    async def close(self) -> None:
        """Закрывает HTTP-клиент провайдера (если есть)."""
        close = getattr(self._provider, "close", None)
        if close is not None:
            await close()

    async def extract(self, text: str) -> ExtractedListing:
        prompt = build_extract_prompt(text)
        last_error = ""
        for attempt in range(1, self._attempts + 1):
            try:
                raw = await self._provider.complete(prompt)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                raise ListingExtractionError(f"LLM request failed: {exc}") from exc
            try:
                return parse_extracted(raw)
            except ValueError as exc:
                last_error = str(exc)
                logger.warning("Bad extraction response", attempt=attempt, error=last_error)
                prompt += "\n\nYour previous reply was not valid. Reply with the JSON object only."
        raise ListingExtractionError(f"invalid LLM response: {last_error}")
