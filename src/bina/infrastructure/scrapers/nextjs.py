"""Данные страниц на Next.js: JSON из ``<script id="__NEXT_DATA__">``.

MyHome.ge и SS.ge отдают объявления прямо в странице этим JSON-ом, поэтому
разбирать вёрстку не нужно.
"""

import json
import re
from collections.abc import Iterator
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

NEXT_DATA_RE = re.compile(
    r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
)


def next_data(html: str) -> dict[str, Any] | None:
    """JSON из ``<script id="__NEXT_DATA__">`` (``None``, если его нет или он битый)."""
    match = NEXT_DATA_RE.search(html)
    if match is None:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        logger.warning("__NEXT_DATA__ is not valid JSON")
        return None
    return data if isinstance(data, dict) else None


def walk(value: Any) -> Iterator[Any]:
    """Все вложенные значения JSON (обход в глубину)."""
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)
