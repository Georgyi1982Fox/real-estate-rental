from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from src.bina.infrastructure.bot import cli as bot_cli
from src.bina.infrastructure.bot.settings import BotMode, BotSettings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("BOT_TOKEN", "BOT_MODE", "BOT_WEBHOOK_BASE_URL", "BOT_DROP_PENDING_UPDATES"):
        monkeypatch.delenv(name, raising=False)


def test_polling_runs_with_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    run_polling = AsyncMock()
    monkeypatch.setattr(bot_cli, "run_polling", run_polling)

    result = CliRunner().invoke(
        bot_cli.cli, ["polling", "--drop-pending-updates"], env={"BOT_TOKEN": "1:a"}
    )

    assert result.exit_code == 0, result.output
    assert run_polling.await_args is not None
    settings: BotSettings = run_polling.await_args.args[0]
    assert settings.mode is BotMode.POLLING
    assert settings.drop_pending_updates is True


def test_polling_ignores_bot_mode_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Команда определяет режим, даже если BOT_MODE=webhook."""
    run_polling = AsyncMock()
    monkeypatch.setattr(bot_cli, "run_polling", run_polling)

    result = CliRunner().invoke(
        bot_cli.cli, ["polling"], env={"BOT_TOKEN": "1:a", "BOT_MODE": "webhook"}
    )

    assert result.exit_code == 0, result.output
    assert run_polling.await_args is not None
    assert run_polling.await_args.args[0].mode is BotMode.POLLING


def test_webhook_cli_options_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    run_webhook = MagicMock()
    monkeypatch.setattr(bot_cli, "run_webhook", run_webhook)

    result = CliRunner().invoke(
        bot_cli.cli,
        ["webhook", "--host", "127.0.0.1", "--port", "9999"],
        env={"BOT_TOKEN": "1:a", "BOT_WEBHOOK_BASE_URL": "https://x", "BOT_WEBAPP_PORT": "80"},
    )

    assert result.exit_code == 0, result.output
    settings: BotSettings = run_webhook.call_args.args[0]
    assert (settings.mode, settings.webapp_host, settings.webapp_port) == (
        BotMode.WEBHOOK,
        "127.0.0.1",
        9999,
    )
    assert settings.drop_pending_updates is False


@pytest.mark.parametrize(
    ("args", "env", "message"),
    [
        (["polling"], {}, "BOT_TOKEN is required"),
        (["webhook"], {"BOT_TOKEN": "1:a"}, "BOT_WEBHOOK_BASE_URL is required"),
    ],
)
def test_config_errors_are_reported(args: list[str], env: dict[str, str], message: str) -> None:
    result = CliRunner().invoke(bot_cli.cli, args, env=env)

    assert result.exit_code == 1
    assert message in result.output
