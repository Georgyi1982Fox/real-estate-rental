import asyncio
from collections.abc import AsyncIterator

import pytest
from aiogram.methods import SendMessage, SetMyCommands, SetWebhook
from aiohttp.test_utils import TestClient, TestServer

from src.bina.infrastructure.bot.runner import HEALTH_PATH, build_webhook_app
from src.bina.infrastructure.bot.settings import BotMode, BotSettings
from tests.support.telegram import TOKEN

from .conftest import BotHarness

SECRET = "s3cret"
UPDATE = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "date": 0,
        "chat": {"id": 5, "type": "private"},
        "from": {"id": 5, "is_bot": False, "first_name": "A", "language_code": "en"},
        "text": "/help",
    },
}


@pytest.fixture
def webhook_settings() -> BotSettings:
    return BotSettings(
        token=TOKEN,
        mode=BotMode.WEBHOOK,
        webhook_base_url="https://bina.example",
        webhook_secret=SECRET,
        mini_app_url="https://app.example",
    )


@pytest.fixture
async def client(
    harness: BotHarness,
    webhook_settings: BotSettings,
) -> AsyncIterator[TestClient]:  # type: ignore[type-arg]
    harness.dispatcher["settings"] = webhook_settings
    app = build_webhook_app(harness.bot, harness.dispatcher, webhook_settings)
    async with TestClient(TestServer(app)) as test_client:
        yield test_client


async def test_startup_sets_webhook_and_commands(
    client: TestClient,  # type: ignore[type-arg]
    harness: BotHarness,
) -> None:
    [set_webhook] = harness.telegram.of(SetWebhook)
    assert set_webhook.url == "https://bina.example/telegram/webhook"
    assert set_webhook.secret_token == SECRET
    assert set(set_webhook.allowed_updates or []) == {"message", "callback_query"}
    assert len(harness.telegram.of(SetMyCommands)) == 2


async def test_health(client: TestClient) -> None:  # type: ignore[type-arg]
    response = await client.get(HEALTH_PATH)
    assert response.status == 200
    assert await response.json() == {"status": "ok"}


async def test_webhook_rejects_wrong_secret(
    client: TestClient,  # type: ignore[type-arg]
    harness: BotHarness,
) -> None:
    for headers in ({}, {"X-Telegram-Bot-Api-Secret-Token": "wrong"}):
        response = await client.post("/telegram/webhook", json=UPDATE, headers=headers)
        assert response.status == 401
    assert harness.telegram.of(SendMessage) == []


async def test_webhook_processes_update(
    client: TestClient,  # type: ignore[type-arg]
    harness: BotHarness,
) -> None:
    response = await client.post(
        "/telegram/webhook",
        json=UPDATE,
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert response.status == 200

    # Обработка идёт в фоне: ждём завершения задач диспетчера
    for _ in range(50):
        if harness.telegram.of(SendMessage):
            break
        await asyncio.sleep(0.01)
    [reply] = harness.telegram.of(SendMessage)
    assert "rentals in Georgia" in reply.text
    assert 5 in harness.store.users
