"""``/api/me``: владелец видит «Проверку функций» (is_admin)."""

import pytest
from httpx import AsyncClient

from bina.infrastructure.api.settings import ApiConfigError, ApiSettings

from .conftest import BOT_TOKEN, TELEGRAM_USER

OWNER_ID = 555
assert TELEGRAM_USER["id"] == OWNER_ID


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings(bot_token=BOT_TOKEN, admin_ids=(OWNER_ID,))


async def test_owner_is_admin(client: AsyncClient, auth: dict[str, str]) -> None:
    me = (await client.get("/api/me", headers=auth)).json()
    assert me["is_admin"] is True


def test_admin_ids_from_env() -> None:
    assert ApiSettings.from_env({"ADMIN_TELEGRAM_IDS": "1, 2"}).admin_ids == (1, 2)
    assert ApiSettings.from_env({}).admin_ids == ()
    with pytest.raises(ApiConfigError):
        ApiSettings.from_env({"ADMIN_TELEGRAM_IDS": "me"})
