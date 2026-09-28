"""Единый формат ошибок API и номер запроса (TASK-017).

Любая ошибка отдаётся как::

    {"error": {"code": "not_found", "message": "Listing not found", "request_id": "…"}}

- ``code`` — стабильный машинный код (фронтенд переводит сообщения по нему);
- ``message`` — короткое пояснение на английском для разработчика;
- ``details`` — для 422: какие поля неверны;
- ``request_id`` — тот же, что в заголовке ``X-Request-ID`` и в логах сервера.

Необработанные исключения превращаются в 500 без технических деталей:
трассировка пишется только в лог.
"""

import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

logger = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
# Принимаем чужой ID только безопасного вида, иначе генерируем свой
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

ERROR_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    402: "payment_required",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}


def error_code(status_code: int) -> str:
    """Машинный код для HTTP-статуса."""
    return ERROR_CODES.get(status_code, "error" if status_code < 500 else "internal_error")


def request_id(request: Request) -> str:
    """ID текущего запроса (задаётся middleware)."""
    return str(getattr(request.state, "request_id", "") or "")


def error_response(
    request: Request,
    status_code: int,
    message: str,
    *,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Ответ с ошибкой в едином формате."""
    body: dict[str, Any] = {"code": error_code(status_code), "message": message}
    if details:
        body["details"] = details
    rid = request_id(request)
    if rid:
        body["request_id"] = rid
    response = JSONResponse({"error": body}, status_code=status_code, headers=headers)
    if rid:
        response.headers[REQUEST_ID_HEADER] = rid
    return response


def _field(location: tuple[Any, ...] | list[Any]) -> str:
    """``("query", "min_price")`` → ``query.min_price``; ``("body",)`` → ``body``."""
    return ".".join(str(part) for part in location)


async def _http_error(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, StarletteHTTPException)
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    headers = dict(exc.headers) if exc.headers else None
    return error_response(request, exc.status_code, message, headers=headers)


async def _validation_error(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, RequestValidationError)
    details = [
        {"field": _field(item.get("loc", ())), "message": str(item.get("msg", "Invalid value"))}
        for item in exc.errors()
    ]
    return error_response(
        request, status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid request", details=details
    )


async def _unhandled_error(request: Request, exc: Exception) -> Response:
    logger.exception(
        "Unhandled API error",
        method=request.method,
        path=request.url.path,
        request_id=request_id(request),
    )
    return error_response(request, status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")


async def _request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    rid = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
    request.state.request_id = rid
    with structlog.contextvars.bound_contextvars(request_id=rid):
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001 - любая непредвиденная ошибка → 500 без деталей
            # Здесь, а не в exception_handler(Exception): так ответ проходит через CORS
            # (иначе браузер покажет ошибку CORS вместо 500)
            response = await _unhandled_error(request, exc)
    response.headers[REQUEST_ID_HEADER] = rid
    return response


def install_error_handling(app: FastAPI) -> None:
    """Подключает обработчики ошибок и ``X-Request-ID``.

    Вызывать до ``CORSMiddleware``: последний добавленный middleware — внешний,
    и CORS-заголовки должны попасть и в ответы с ошибками.
    """
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.middleware("http")(_request_id_middleware)
