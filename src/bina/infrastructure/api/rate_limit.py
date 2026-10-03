"""Защита API от перегрузки (TASK-019).

Лимиты на посетителя (IP; за Cloudflare — настоящий IP из ``CF-Connecting-IP``):
общий — ``API_RATE_LIMIT`` запросов в минуту, для «тяжёлых» запросов (PDF, AI,
оплата, жалобы, загрузка фото, умный поиск) — ``API_HEAVY_RATE_LIMIT``.
Сверх лимита — 429 с ``Retry-After``.
"""

import ipaddress
import math
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response, status

from bina.infrastructure.api.errors import error_response
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.ratelimit import SlidingWindowLimiter

WINDOW_SECONDS = 60
EXEMPT_PATHS = frozenset({"/api/health"})
# (метод, конец пути) «тяжёлых» запросов
HEAVY = (
    ("POST", "/contract"),
    ("POST", "/assistant"),
    ("POST", "/api/documents/acceptance"),
    ("POST", "/api/subscription/invoice"),
    ("POST", "/complaints"),
    ("POST", "/api/referral/apply"),
    # Загрузка фото и логотипа: большие тела и обработка картинок
    ("POST", "/photos"),
    ("POST", "/agency/logo"),
)


def client_key(request: Request) -> str:
    """Кто прислал запрос: IP посетителя.

    Заголовку Cloudflare (``CF-Connecting-IP``) верим, только если запрос пришёл с этого же
    компьютера или из сети Docker (туннель Cloudflare). Иначе его подставил бы кто угодно и
    обходил лимиты, меняя «свой IP» в каждом запросе.
    """
    peer = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("cf-connecting-ip", "").strip()
    if forwarded and _local(peer):
        return forwarded
    return peer


def _local(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # Тестовый клиент и unix-сокет — не IP
        return True
    return address.is_loopback or address.is_private


def is_heavy(request: Request) -> bool:
    path = request.url.path
    if request.method == "GET" and request.query_params.get("sort") == "smart":
        return True  # умный поиск: запрос к AI на каждый вызов
    return any(request.method == method and path.endswith(end) for method, end in HEAVY)


def install_rate_limit(app: FastAPI, settings: ApiSettings) -> None:
    """Лимиты хранятся в ``app.state`` — у каждого приложения (и теста) свои."""
    app.state.rate_limiter = SlidingWindowLimiter(settings.rate_limit, WINDOW_SECONDS)
    app.state.heavy_rate_limiter = SlidingWindowLimiter(settings.heavy_rate_limit, WINDOW_SECONDS)

    @app.middleware("http")
    async def _limit(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == "OPTIONS" or request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        key = client_key(request)
        wait = request.app.state.rate_limiter.hit(key)
        if wait is None and is_heavy(request):
            wait = request.app.state.heavy_rate_limiter.hit(key)
        if wait is not None:
            seconds = max(1, math.ceil(wait))
            return error_response(
                request,
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Too many requests, try again in {seconds} s",
                headers={"Retry-After": str(seconds)},
            )
        return await call_next(request)
