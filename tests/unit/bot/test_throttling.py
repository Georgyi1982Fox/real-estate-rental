"""Защита бота от флуда (TASK-019)."""

import pytest
from aiogram.methods import SendMessage

from bina.infrastructure.bot.settings import BotSettings
from tests.support.telegram import TOKEN

from .conftest import BotHarness


@pytest.fixture
def settings() -> BotSettings:
    return BotSettings(token=TOKEN, page_size=3, rate_limit=3)


async def test_flood_is_dropped_with_one_warning(harness: BotHarness) -> None:
    for _ in range(3):
        await harness.send("/help")
    assert len(harness.telegram.of(SendMessage)) == 3
    harness.reset()

    for _ in range(4):
        await harness.send("/help")
    texts = harness.sent_texts()
    assert texts == ["⏳ Слишком много сообщений подряд. Подождите несколько секунд."]
    # Лишние апдейты не открывали сессию БД
    assert len(harness.sessions) == 3
