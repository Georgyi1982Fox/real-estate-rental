"""TASK-124: владельцу — свой адрес Mini App (если основной у него не открывается)."""

from unittest.mock import AsyncMock

import pytest
from aiogram.methods import SetChatMenuButton
from aiogram.types import MenuButtonWebApp

from bina.infrastructure.bot.factory import setup_bot_ui
from bina.infrastructure.bot.notifications import TelegramNotificationSender
from bina.infrastructure.bot.settings import BotSettings
from tests.support.telegram import CHAT_ID, TOKEN

from .conftest import BotHarness
from .test_notifications_sender import pending

PUBLIC = "https://bina.example/"
OWNER = "https://owner.ru.tuna.am"


def test_settings_for_user() -> None:
    settings = BotSettings.from_env(
        {
            "BOT_TOKEN": TOKEN,
            "BOT_MINI_APP_URL": PUBLIC,
            "BOT_OWNER_MINI_APP_URL": OWNER,
            "ADMIN_TELEGRAM_IDS": "111",
        }
    )
    assert settings.for_user(111).mini_app_url == OWNER
    assert settings.for_user(222).mini_app_url == PUBLIC
    assert settings.for_user(None).mini_app_url == PUBLIC
    # Без своего адреса владелец открывает общий
    plain = BotSettings(token=TOKEN, mini_app_url=PUBLIC, admin_ids=(111,))
    assert plain.for_user(111) is plain


def app_urls(harness: BotHarness) -> list[str]:
    markup = harness.last_markup()
    return [
        button.web_app.url
        for row in markup.inline_keyboard
        for button in row
        if button.web_app is not None
    ]


@pytest.mark.parametrize(("admin", "expected"), [(CHAT_ID, OWNER), (999, PUBLIC)])
async def test_menu_buttons_use_owner_url(harness: BotHarness, admin: int, expected: str) -> None:
    harness.dispatcher["settings"] = BotSettings(
        token=TOKEN, mini_app_url=PUBLIC, owner_mini_app_url=OWNER, admin_ids=(admin,)
    )
    await harness.send("/start")
    urls = app_urls(harness)
    assert urls
    assert all(url.startswith(expected.rstrip("/")) for url in urls)


async def test_owner_menu_button_in_his_chat(harness: BotHarness) -> None:
    harness.reset()
    await setup_bot_ui(
        harness.bot,
        BotSettings(token=TOKEN, mini_app_url=PUBLIC, owner_mini_app_url=OWNER, admin_ids=(111,)),
    )
    calls = [call for call in harness.telegram.of(SetChatMenuButton)]
    assert isinstance(calls[0], SetChatMenuButton)
    by_chat = {
        call.chat_id: call.menu_button
        for call in calls
        if isinstance(call, SetChatMenuButton) and isinstance(call.menu_button, MenuButtonWebApp)
    }
    assert by_chat[None].web_app.url == PUBLIC
    assert by_chat[111].web_app.url == OWNER

    # Адрес владельца убрали из .env — в его чате снова общая кнопка
    harness.reset()
    await setup_bot_ui(harness.bot, BotSettings(token=TOKEN, mini_app_url=PUBLIC, admin_ids=(111,)))
    resets = [
        call
        for call in harness.telegram.of(SetChatMenuButton)
        if isinstance(call, SetChatMenuButton) and call.chat_id == 111
    ]
    assert [call.menu_button for call in resets] == [None]


@pytest.mark.parametrize(("owner_ids", "expected"), [((555,), OWNER), ((1,), PUBLIC)])
async def test_notifications_to_owner(owner_ids: tuple[int, ...], expected: str) -> None:
    bot = AsyncMock()
    sender = TelegramNotificationSender(
        bot, PUBLIC, send_interval=0, owner_mini_app_url=OWNER, owner_ids=owner_ids
    )
    await sender.send(pending())  # telegram_id=555
    markup = bot.send_message.await_args.kwargs["reply_markup"]
    button = markup.inline_keyboard[0][0]
    assert button.web_app is not None
    assert button.web_app.url.startswith(expected.rstrip("/") + "/listing/")
