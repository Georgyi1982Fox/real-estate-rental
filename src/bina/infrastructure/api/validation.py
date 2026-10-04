"""Валидация и очистка входных данных API (TASK-018).

Текст пользователя (например, название сохранённого поиска) очищается от
HTML-тегов и управляющих символов. Фронтенд (React) и бот (HTML-экранирование)
и так выводят его безопасно; очистка — второй рубеж защиты от XSS и мусора в БД.
"""

import re
import unicodedata

from fastapi import FastAPI, Request, status
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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


def _limit_for(path: str) -> int:
    # TASK-096, TASK-100: фото объявления и логотип агентства — большие тела, только тут
    return MAX_PHOTO_BODY_BYTES if path.endswith(("/photos", "/agency/logo")) else MAX_BODY_BYTES


class BodyLimitMiddleware:
    """Тело запроса не больше лимита (413).

    Длину из ``Content-Length`` проверяем сразу. Тело частями (``Transfer-Encoding: chunked``,
    без длины — так прокси сайта отправляет даже пустой POST) считаем по мере чтения и
    обрываем, как только лимит превышен: обойти проверку так нельзя.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = _limit_for(scope["path"])
        headers = dict(scope["headers"])
        length = headers.get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > limit):
            await self._too_large(scope, receive, send, limit)
            return

        received = 0
        started = rejected = False

        async def counting_receive() -> Message:
            nonlocal received, rejected
            message = await receive()
            if message["type"] == "http.request" and not rejected:
                received += len(message.get("body", b""))
                if received > limit:
                    # Отвечаем 413 сами и дальше тело не читаем: приложению — «клиент ушёл»
                    rejected = True
                    if not started:
                        await self._too_large(scope, receive, send, limit)
                    return {"type": "http.disconnect"}
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if rejected:
                return  # ответ 413 уже отправлен
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except Exception:
            if not rejected:
                raise

    async def _too_large(self, scope: Scope, receive: Receive, send: Send, limit: int) -> None:
        response = error_response(
            Request(scope),
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Request body is larger than {limit} bytes",
        )
        await response(scope, receive, send)


def install_body_limit(app: FastAPI) -> None:
    """Отклонять запросы с телом больше ``MAX_BODY_BYTES`` (413)."""
    app.add_middleware(BodyLimitMiddleware)
