"""CLI бота: ``bina-bot polling`` и ``bina-bot webhook``."""

import asyncio
import dataclasses
import logging

import click

from src.bina.infrastructure.bot.runner import run_polling, run_webhook
from src.bina.infrastructure.bot.settings import BotConfigError, BotMode, BotSettings


def _load_settings(mode: BotMode, **overrides: object) -> BotSettings:
    """Читает настройки из окружения и применяет опции командной строки."""
    try:
        base = BotSettings.from_env(mode=mode)
        changes = {key: value for key, value in overrides.items() if value is not None}
        return dataclasses.replace(base, **changes)  # type: ignore[arg-type]
    except BotConfigError as exc:
        raise click.ClickException(str(exc)) from exc


@click.group()
@click.option(
    "--log-level",
    default="INFO",
    show_default=True,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Уровень логирования.",
)
def cli(log_level: str) -> None:
    """Telegram-бот Bina.ai. Настройки берутся из переменных окружения BOT_*."""
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@cli.command()
@click.option(
    "--drop-pending-updates",
    is_flag=True,
    default=None,
    help="Пропустить апдейты, накопившиеся пока бот был выключен.",
)
def polling(drop_pending_updates: bool | None) -> None:
    """Запустить бота в режиме long polling (для разработки)."""
    settings = _load_settings(BotMode.POLLING, drop_pending_updates=drop_pending_updates)
    asyncio.run(run_polling(settings))


@cli.command()
@click.option("--host", default=None, help="Адрес сервера (по умолчанию BOT_WEBAPP_HOST).")
@click.option("--port", default=None, type=int, help="Порт сервера (по умолчанию BOT_WEBAPP_PORT).")
@click.option(
    "--drop-pending-updates",
    is_flag=True,
    default=None,
    help="Пропустить апдейты, накопившиеся пока бот был выключен.",
)
def webhook(host: str | None, port: int | None, drop_pending_updates: bool | None) -> None:
    """Запустить aiohttp-сервер вебхука (нужен BOT_WEBHOOK_BASE_URL)."""
    settings = _load_settings(
        BotMode.WEBHOOK,
        webapp_host=host,
        webapp_port=port,
        drop_pending_updates=drop_pending_updates,
    )
    run_webhook(settings)


def main() -> None:
    """Точка входа ``bina-bot``."""
    cli()


if __name__ == "__main__":
    main()
