"""AI-анализ фото квартиры через OpenAI-совместимый API с картинками (TASK-114).

``POST {base_url}/chat/completions``: текст задания и до 4 фото (``detail: low`` —
дёшево, для оценки ремонта хватает). Фото с сайтов передаются ссылкой, фото
собственников (``/api/media/…`` — лежат у нас) — содержимым в base64.
Ответ — JSON, проверяется Pydantic; при кривом ответе — ещё попытка.
"""

import base64
import json
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field, ValidationError

from bina.application.photo_analysis import (
    ISSUES,
    REPAIR_LEVELS,
    SUMMARY_LANGUAGES,
    PhotoReport,
    photos_for_analysis,
)
from bina.application.ports.photo_analyzer import IPhotoAnalyzer, PhotoAnalysisError
from bina.infrastructure.llm.providers.qwen_provider import AITUNNEL_BASE_URL
from bina.infrastructure.storage.photos import MEDIA_URL, media_dir

logger = structlog.get_logger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

PROMPT = f"""You inspect photos of an apartment offered for rent in Georgia (Tbilisi, Batumi).
Judge only what is visible in the photos. Do not guess about things you cannot see.

Reply with ONLY a JSON object, no markdown:
{{"level": "...", "issues": ["..."], "summary": {{"ru": "...", "en": "...", "ka": "..."}}}}

- "level": one of {", ".join(REPAIR_LEVELS)}:
  excellent — new or very fresh renovation, everything looks new;
  good — normal lived-in condition, nothing serious;
  needs_repair — old renovation, visible damage, would need work.
- "issues": zero or more of {", ".join(ISSUES)} — only if clearly visible.
- "summary": 2-3 short sentences per language (Russian, English, Georgian in Georgian
  script) for a tenant: overall condition, what looks good, what to check at the viewing.
"""


class _Report(BaseModel):
    level: str
    issues: list[str] = Field(default_factory=list)
    summary: dict[str, str] = Field(default_factory=dict)


def parse_report(raw: str) -> PhotoReport:
    """Вывод AI из ответа; ``ValueError`` — ответ не тот."""
    match = JSON_OBJECT_RE.search(raw)
    if match is None:
        raise ValueError("no JSON object in the response")
    try:
        data = _Report.model_validate(json.loads(match.group(0)))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"invalid response: {exc}") from exc
    if data.level not in REPAIR_LEVELS:
        raise ValueError(f"unknown level {data.level!r}")
    issues = tuple(dict.fromkeys(code for code in data.issues if code in ISSUES))
    summary = {
        language: data.summary[language].strip()
        for language in SUMMARY_LANGUAGES
        if isinstance(data.summary.get(language), str) and data.summary[language].strip()
    }
    return PhotoReport(level=data.level, issues=issues, summary=summary)


def image_url(url: str, root: Path | None = None) -> str | None:
    """Ссылка для AI: сайт — как есть; своё фото — содержимым (data URL); иначе None."""
    if url.startswith(("http://", "https://")):
        return url
    prefix = MEDIA_URL + "/"
    if not url.startswith(prefix):
        return None
    base = (root or media_dir()).resolve()
    path = (base / url.removeprefix(prefix)).resolve()
    if base not in path.parents or not path.is_file():
        return None
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


class LLMPhotoAnalyzer(IPhotoAnalyzer):
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = AITUNNEL_BASE_URL,
        timeout: int = 90,
        attempts: int = 2,
        client: httpx.AsyncClient | None = None,
        media_root: Path | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.attempts = attempts
        self.media_root = media_root
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout, headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def analyze(self, images: Sequence[str]) -> PhotoReport:
        urls = [
            url
            for url in (image_url(image, self.media_root) for image in photos_for_analysis(images))
            if url is not None
        ]
        if not urls:
            raise PhotoAnalysisError("no photos to analyze")
        prompt = PROMPT
        last_error = ""
        for attempt in range(1, self.attempts + 1):
            raw = await self._ask(prompt, urls)
            try:
                return parse_report(raw)
            except ValueError as exc:
                last_error = str(exc)
                logger.warning("Bad photo analysis response", attempt=attempt, error=last_error)
                prompt = PROMPT + "\nYour previous reply was not valid. Reply with the JSON only."
        raise PhotoAnalysisError(f"invalid response: {last_error}")

    async def _ask(self, prompt: str, urls: list[str]) -> str:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        content += [
            {"type": "image_url", "image_url": {"url": url, "detail": "low"}} for url in urls
        ]
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": content}],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            detail = exc.response.text[:300] if isinstance(exc, httpx.HTTPStatusError) else ""
            logger.warning("Photo analysis request failed", error=str(exc), response=detail)
            raise PhotoAnalysisError(str(exc) or type(exc).__name__) from exc


def photo_analysis_configured() -> bool:
    return bool(os.getenv("PHOTO_API_KEY") or os.getenv("LLM_API_KEY"))


def create_photo_analyzer() -> LLMPhotoAnalyzer:
    """Ключ и адрес — как у перевода (``LLM_API_KEY``, ``LLM_BASE_URL``, по умолчанию
    AITUNNEL); свои — ``PHOTO_API_KEY`` / ``PHOTO_BASE_URL``. Модель — ``PHOTO_MODEL``
    (по умолчанию gpt-4o-mini: видит картинки и недорогая)."""
    return LLMPhotoAnalyzer(
        api_key=os.getenv("PHOTO_API_KEY") or os.getenv("LLM_API_KEY") or "",
        model=os.getenv("PHOTO_MODEL") or DEFAULT_MODEL,
        base_url=os.getenv("PHOTO_BASE_URL") or os.getenv("LLM_BASE_URL") or AITUNNEL_BASE_URL,
    )
