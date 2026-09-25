import pytest

from bina.infrastructure.bot.settings import BotConfigError, BotMode, BotSettings


def test_defaults() -> None:
    settings = BotSettings.from_env({"BOT_TOKEN": "1:abc"})

    assert settings.mode is BotMode.POLLING
    assert settings.page_size == 5
    assert settings.webhook_path == "/telegram/webhook"
    assert settings.drop_pending_updates is False
    assert settings.mini_app_url is None


def test_full_webhook_config() -> None:
    settings = BotSettings.from_env(
        {
            "BOT_TOKEN": "1:abc",
            "BOT_MODE": "WEBHOOK",
            "BOT_WEBHOOK_BASE_URL": "https://bina.example/",
            "BOT_WEBHOOK_PATH": "/tg",
            "BOT_WEBHOOK_SECRET": "s",
            "BOT_WEBAPP_PORT": "9000",
            "BOT_PAGE_SIZE": "7",
            "BOT_DROP_PENDING_UPDATES": "true",
            "BOT_MINI_APP_URL": "https://app.example",
        }
    )

    assert settings.mode is BotMode.WEBHOOK
    assert settings.webhook_url == "https://bina.example/tg"
    assert settings.webapp_port == 9000
    assert settings.page_size == 7
    assert settings.drop_pending_updates is True


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({}, "BOT_TOKEN is required"),
        ({"BOT_TOKEN": "  "}, "BOT_TOKEN is required"),
        ({"BOT_TOKEN": "1:a", "BOT_MODE": "push"}, "BOT_MODE"),
        ({"BOT_TOKEN": "1:a", "BOT_PAGE_SIZE": "abc"}, "BOT_PAGE_SIZE must be an integer"),
        ({"BOT_TOKEN": "1:a", "BOT_PAGE_SIZE": "11"}, "BOT_PAGE_SIZE must be in"),
        ({"BOT_TOKEN": "1:a", "BOT_WEBAPP_PORT": "x"}, "BOT_WEBAPP_PORT"),
        ({"BOT_TOKEN": "1:a", "BOT_WEBHOOK_PATH": "tg"}, "must start with '/'"),
        ({"BOT_TOKEN": "1:a", "BOT_MODE": "webhook"}, "BOT_WEBHOOK_BASE_URL is required"),
    ],
)
def test_invalid_config(env: dict[str, str], message: str) -> None:
    with pytest.raises(BotConfigError, match=message):
        BotSettings.from_env(env)


def test_explicit_mode_overrides_env() -> None:
    settings = BotSettings.from_env(
        {"BOT_TOKEN": "1:a", "BOT_MODE": "webhook"},
        mode=BotMode.POLLING,
    )
    assert settings.mode is BotMode.POLLING


def test_webhook_url_requires_base_url() -> None:
    with pytest.raises(BotConfigError):
        _ = BotSettings(token="1:a").webhook_url
