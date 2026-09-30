"""Валидация и очистка входных данных API (TASK-018).

Текст пользователя (например, название сохранённого поиска) очищается от
HTML-тегов и управляющих символов. Фронтенд (React) и бот (HTML-экранирование)
и так выводят его безопасно; очистка — второй рубеж защиты от XSS и мусора в БД.
"""

import re
import unicodedata
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from starlette.responses import Response

from bina.infrastructure.api.errors import error_response

# Больше API не принимает (самое большое тело — сохранённый поиск, это сотни байт)
MAX_BODY_BYTES = 64 * 1024
# Загрузка фото объявления (POST /api/my/listings/{id}/photos)
MAX_PHOTO_BODY_BYTES = 15 * 1024 * 1024

_TAG_RE = re.compile(r"<[^>]*>")
_SPACES_RE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    """Текст без HTML-тегов, управляющих символов и лишних пробелов."""
    without_tags = _TAG_RE.sub(" ", value)
    printable = "".join(
        char
        for char in without_tags
        if char in "\n\t" or not unicodedata.category(char).startswith("C")
    )
    # Оставшиеся угловые скобки (незакрытый тег) — не нужны в названиях
    printable = printable.replace("<", " ").replace(">", " ")
    return _SPACES_RE.sub(" ", printable).strip()


async def _limit_body_size(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    length = request.headers.get("content-length")
    # TASK-096: фото собственника — большое тело, но только на этот адрес
    limit = MAX_PHOTO_BODY_BYTES if request.url.path.endswith("/photos") else MAX_BODY_BYTES
    if length is not None and (not length.isdigit() or int(length) > limit):
        return error_response(
            request,
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Request body is larger than {limit} bytes",
        )
    return await call_next(request)


def install_body_limit(app: FastAPI) -> None:
    """Отклонять запросы с телом больше ``MAX_BODY_BYTES`` (413)."""
    app.middleware("http")(_limit_body_size)
