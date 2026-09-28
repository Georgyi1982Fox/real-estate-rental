"""Единый формат ошибок, X-Request-ID, лимит тела и очистка текста (TASK-017/018)."""

import logging
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.infrastructure.api.schemas import SearchIn, SearchPatchIn
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.api.validation import MAX_BODY_BYTES, clean_text

from .conftest import BOT_TOKEN


def error(response: Any) -> dict[str, Any]:
    body = response.json()
    assert set(body) == {"error"}, body
    return cast(dict[str, Any], body["error"])


async def test_not_found_format_and_request_id(client: AsyncClient) -> None:
    response = await client.get("/api/listings/not-a-uuid")

    assert response.status_code == 404
    body = error(response)
    assert (body["code"], body["message"]) == ("not_found", "Listing not found")
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert len(body["request_id"]) == 32


async def test_incoming_request_id_is_kept_if_safe(client: AsyncClient) -> None:
    kept = await client.get("/api/health", headers={"X-Request-ID": "front-1234abcd"})
    assert kept.headers["X-Request-ID"] == "front-1234abcd"

    replaced = await client.get("/api/health", headers={"X-Request-ID": "<script>"})
    assert replaced.headers["X-Request-ID"] != "<script>"


async def test_unauthorized(client: AsyncClient) -> None:
    body = error(await client.get("/api/favorites"))
    assert body["code"] == "unauthorized"


async def test_validation_details(client: AsyncClient) -> None:
    response = await client.get("/api/listings", params={"per_page": "0", "sort": "cheap"})

    assert response.status_code == 422
    body = error(response)
    assert (body["code"], body["message"]) == ("validation_error", "Invalid request")
    assert {item["field"] for item in body["details"]} == {"query.per_page", "query.sort"}


async def test_custom_422_and_unknown_route_and_method(client: AsyncClient) -> None:
    bad = await client.get("/api/listings", params={"min_price": "abc"})
    assert (bad.status_code, error(bad)["message"]) == (422, "min_price must be a number")

    missing = await client.get("/api/nope")
    assert (missing.status_code, error(missing)["code"]) == (404, "not_found")

    method = await client.put("/api/listings")
    assert (method.status_code, error(method)["code"]) == (405, "method_not_allowed")


async def test_body_too_large(client: AsyncClient) -> None:
    response = await client.post(
        "/api/favorites",
        content=b"x" * (MAX_BODY_BYTES + 1),
        headers={"Content-Type": "application/json"},
    )
    assert (response.status_code, error(response)["code"]) == (413, "payload_too_large")


async def test_unhandled_error_hides_details(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app(
        ApiSettings(bot_token=BOT_TOKEN), cast(async_sessionmaker[AsyncSession], MagicMock())
    )

    @app.get("/api/boom")
    async def boom() -> None:
        raise RuntimeError("secret database password")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with caplog.at_level(logging.ERROR):
            response = await client.get("/api/boom")

    assert response.status_code == 500
    body = error(response)
    assert (body["code"], body["message"]) == ("internal_error", "Internal server error")
    assert "secret" not in response.text
    assert body["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Ваке <b>2</b> комн. ", "Ваке 2 комн."),
        ("<script>alert(1)</script>", "alert(1)"),
        ("a\x00b​c", "abc"),
        ("Ваке <img src=x onerror=1", "Ваке img src=x onerror=1"),
        ("   ", ""),
    ],
)
def test_clean_text(raw: str, expected: str) -> None:
    assert clean_text(raw) == expected


def test_search_names_are_cleaned() -> None:
    assert SearchIn(name=" <i>Моя</i>  Ваке ").name == "Моя Ваке"
    assert SearchIn(name="<br>").name is None  # пустое → название из фильтров
    assert SearchPatchIn(name="<b>Дом</b>").name == "Дом"
    with pytest.raises(ValueError, match="visible text"):
        SearchPatchIn(name="<br>")


async def test_error_responses_carry_cors_headers() -> None:
    app = create_app(
        ApiSettings(bot_token=BOT_TOKEN), cast(async_sessionmaker[AsyncSession], MagicMock())
    )

    @app.get("/api/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    origin = {"Origin": "https://georgyi1982fox.github.io"}
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        responses = [
            await client.get("/api/boom", headers=origin),
            await client.get("/api/nope", headers=origin),
            await client.post(
                "/api/favorites",
                content=b"x" * (MAX_BODY_BYTES + 1),
                headers={**origin, "Content-Type": "application/json"},
            ),
        ]
    assert [response.status_code for response in responses] == [500, 404, 413]
    for response in responses:
        assert response.headers["access-control-allow-origin"] == origin["Origin"]
        assert "x-request-id" in response.headers.get("access-control-expose-headers", "").lower()
