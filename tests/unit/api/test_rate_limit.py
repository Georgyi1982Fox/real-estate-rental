"""Защита API от перегрузки (TASK-019)."""

import pytest
from httpx import AsyncClient

from bina.infrastructure.api.settings import ApiConfigError, ApiSettings

from .conftest import BOT_TOKEN


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings(bot_token=BOT_TOKEN, rate_limit=5, heavy_rate_limit=2)


async def test_general_limit(client: AsyncClient) -> None:
    codes = [(await client.get("/api/districts")).status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]
    limited = await client.get("/api/districts")
    assert limited.status_code == 429
    assert "Too many requests" in limited.json()["error"]["message"]
    assert int(limited.headers["Retry-After"]) >= 1
    # Проверка здоровья не ограничивается
    assert (await client.get("/api/health")).status_code == 200
    # Другой посетитель (Cloudflare передаёт его IP) — свой лимит
    other = await client.get("/api/districts", headers={"CF-Connecting-IP": "203.0.113.7"})
    assert other.status_code == 200


async def test_heavy_limit(client: AsyncClient, auth: dict[str, str]) -> None:
    url = "/api/listings/00000000-0000-0000-0000-000000000000/complaints"
    codes = [
        (await client.post(url, json={"reason": "fraud"}, headers=auth)).status_code
        for _ in range(3)
    ]
    # Первые две доходят до обработчика (объявления нет — 404), третья — лимит
    assert codes == [404, 404, 429]


def test_settings_from_env() -> None:
    settings = ApiSettings.from_env({"API_RATE_LIMIT": "0", "API_HEAVY_RATE_LIMIT": "7"})
    assert (settings.rate_limit, settings.heavy_rate_limit) == (0, 7)
    assert ApiSettings.from_env({}).rate_limit == 120
    with pytest.raises(ApiConfigError):
        ApiSettings.from_env({"API_RATE_LIMIT": "many"})
