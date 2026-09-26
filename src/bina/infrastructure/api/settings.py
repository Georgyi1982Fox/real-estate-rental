import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_CORS_ORIGINS: tuple[str, ...] = ("https://georgyi1982fox.github.io",)
DEFAULT_INIT_DATA_MAX_AGE = 24 * 60 * 60


class ApiConfigError(ValueError):
    """Некорректная конфигурация API."""


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Настройки REST API.

    Читаются из переменных окружения через :meth:`from_env`:

    - ``API_CORS_ORIGINS``: разрешённые origin через запятую
      (по умолчанию ``https://georgyi1982fox.github.io``)
    - ``BOT_TOKEN``: токен бота, нужен для проверки подписи ``X-Telegram-Init-Data``
    - ``API_INIT_DATA_MAX_AGE``: срок жизни initData в секундах (по умолчанию сутки)
    - ``API_ALLOW_INSECURE_USER_ID``: ``1``/``true``, разрешить ``?user_id=`` без
      подписи Telegram. **Только для локальной разработки**: любой сможет
      действовать от имени любого пользователя.
    """

    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    bot_token: str | None = None
    init_data_max_age: int = DEFAULT_INIT_DATA_MAX_AGE
    allow_insecure_user_id: bool = False

    def __post_init__(self) -> None:
        """Проверяет согласованность настроек."""
        if self.init_data_max_age <= 0:
            raise ApiConfigError("API_INIT_DATA_MAX_AGE must be positive")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ApiSettings":
        """Создаёт настройки из переменных окружения.

        Raises:
            ApiConfigError: если значения некорректны.
        """
        source = os.environ if env is None else env

        def get(name: str) -> str | None:
            value = source.get(name, "").strip()
            return value or None

        origins = get("API_CORS_ORIGINS")
        max_age = get("API_INIT_DATA_MAX_AGE")
        try:
            init_data_max_age = int(max_age) if max_age else DEFAULT_INIT_DATA_MAX_AGE
        except ValueError as exc:
            raise ApiConfigError(
                f"API_INIT_DATA_MAX_AGE must be an integer, got {max_age!r}"
            ) from exc

        return cls(
            cors_origins=(
                tuple(o.strip().rstrip("/") for o in origins.split(",") if o.strip())
                if origins
                else DEFAULT_CORS_ORIGINS
            ),
            bot_token=get("BOT_TOKEN"),
            init_data_max_age=init_data_max_age,
            allow_insecure_user_id=(get("API_ALLOW_INSECURE_USER_ID") or "").lower()
            in {"1", "true", "yes"},
        )
