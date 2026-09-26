import pytest
from httpx import AsyncClient

from bina.infrastructure.api.settings import ApiConfigError, ApiSettings

from .conftest import ORIGIN


async def test_cors_preflight_from_frontend(client: AsyncClient) -> None:
    response = await client.options(
        "/api/favorites",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-telegram-init-data,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "X-Telegram-Init-Data" in response.headers["access-control-allow-headers"]


async def test_cors_rejects_other_origins(client: AsyncClient) -> None:
    response = await client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_settings_defaults() -> None:
    settings = ApiSettings.from_env({})
    assert settings.cors_origins == (ORIGIN,)
    assert settings.bot_token is None
    assert settings.allow_insecure_user_id is False
    assert settings.init_data_max_age == 24 * 60 * 60


def test_settings_from_env() -> None:
    settings = ApiSettings.from_env(
        {
            "API_CORS_ORIGINS": "https://a.example/, http://localhost:5173",
            "BOT_TOKEN": "1:abc",
            "API_INIT_DATA_MAX_AGE": "600",
            "API_ALLOW_INSECURE_USER_ID": "true",
        }
    )
    assert settings.cors_origins == ("https://a.example", "http://localhost:5173")
    assert settings.bot_token == "1:abc"
    assert settings.init_data_max_age == 600
    assert settings.allow_insecure_user_id is True


@pytest.mark.parametrize("value", ["abc", "0", "-5"])
def test_invalid_max_age(value: str) -> None:
    with pytest.raises(ApiConfigError):
        ApiSettings.from_env({"API_INIT_DATA_MAX_AGE": value})
