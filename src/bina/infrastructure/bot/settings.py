import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class BotMode(StrEnum):
    """Режим получения апдейтов."""

    POLLING = "polling"
    WEBHOOK = "webhook"


class BotConfigError(ValueError):
    """Некорректная конфигурация бота."""


@dataclass(frozen=True, slots=True)
class BotSettings:
    """Настройки Telegram-бота.

    Читаются из переменных окружения через :meth:`from_env`:

    - ``BOT_TOKEN`` (обязательно)
    - ``BOT_MODE``: ``polling`` | ``webhook`` (по умолчанию ``polling``)
    - ``BOT_WEBHOOK_BASE_URL``: публичный HTTPS-адрес, обязателен для webhook
    - ``BOT_WEBHOOK_PATH`` (по умолчанию ``/telegram/webhook``)
    - ``BOT_WEBHOOK_SECRET``: секрет для заголовка ``X-Telegram-Bot-Api-Secret-Token``
    - ``BOT_WEBAPP_HOST`` / ``BOT_WEBAPP_PORT``: адрес aiohttp-сервера (``0.0.0.0:8080``)
    - ``BOT_MINI_APP_URL``: URL Telegram Mini App (кнопка меню)
    - ``BOT_PAGE_SIZE``: объявлений на страницу (1-10, по умолчанию 5)
    - ``BOT_DROP_PENDING_UPDATES``: ``1``/``true``, пропустить накопившиеся апдейты
    """

    token: str
    mode: BotMode = BotMode.POLLING
    webhook_base_url: str | None = None
    webhook_path: str = "/telegram/webhook"
    webhook_secret: str | None = None
    webapp_host: str = "0.0.0.0"
    webapp_port: int = 8080
    mini_app_url: str | None = None
    page_size: int = 5
    drop_pending_updates: bool = False

    def __post_init__(self) -> None:
        """Проверяет согласованность настроек."""
        if not self.token:
            raise BotConfigError("BOT_TOKEN is required")
        if not 1 <= self.page_size <= 10:
            raise BotConfigError("BOT_PAGE_SIZE must be in [1, 10]")
        if not self.webhook_path.startswith("/"):
            raise BotConfigError("BOT_WEBHOOK_PATH must start with '/'")
        if self.mode is BotMode.WEBHOOK and not self.webhook_base_url:
            raise BotConfigError("BOT_WEBHOOK_BASE_URL is required in webhook mode")

    @property
    def webhook_url(self) -> str:
        """Полный URL вебхука, который регистрируется в Telegram."""
        if not self.webhook_base_url:
            raise BotConfigError("BOT_WEBHOOK_BASE_URL is not set")
        return self.webhook_base_url.rstrip("/") + self.webhook_path

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "BotSettings":
        """Создаёт настройки из переменных окружения.

        Raises:
            BotConfigError: если настройки отсутствуют или некорректны.
        """
        source = os.environ if env is None else env

        def get(name: str) -> str | None:
            value = source.get(name, "").strip()
            return value or None

        try:
            mode = BotMode((get("BOT_MODE") or BotMode.POLLING).lower())
            port = int(get("BOT_WEBAPP_PORT") or 8080)
            page_size = int(get("BOT_PAGE_SIZE") or 5)
        except ValueError as exc:
            raise BotConfigError(str(exc)) from exc

        return cls(
            token=get("BOT_TOKEN") or "",
            mode=mode,
            webhook_base_url=get("BOT_WEBHOOK_BASE_URL"),
            webhook_path=get("BOT_WEBHOOK_PATH") or "/telegram/webhook",
            webhook_secret=get("BOT_WEBHOOK_SECRET"),
            webapp_host=get("BOT_WEBAPP_HOST") or "0.0.0.0",
            webapp_port=port,
            mini_app_url=get("BOT_MINI_APP_URL"),
            page_size=page_size,
            drop_pending_updates=(get("BOT_DROP_PENDING_UPDATES") or "").lower()
            in {"1", "true", "yes"},
        )
