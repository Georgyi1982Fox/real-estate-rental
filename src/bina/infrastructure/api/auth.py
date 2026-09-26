"""Определение пользователя по подписанному Telegram ``initData``.

Mini App передаёт строку ``Telegram.WebApp.initData`` в заголовке
``X-Telegram-Init-Data``. Подпись проверяется токеном бота, поэтому подделать
пользователя нельзя (в отличие от ``?user_id=``, который может прислать кто угодно).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from aiogram.utils.web_app import safe_parse_webapp_init_data
from fastapi import HTTPException, status

from bina.infrastructure.api.settings import ApiSettings

INIT_DATA_HEADER = "X-Telegram-Init-Data"


@dataclass(frozen=True, slots=True)
class TelegramIdentity:
    """Пользователь Telegram, от имени которого выполняется запрос."""

    telegram_id: int
    language_code: str | None = None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def verify_init_data(
    init_data: str,
    bot_token: str,
    max_age: timedelta,
    now: datetime | None = None,
) -> TelegramIdentity:
    """Проверяет подпись и свежесть initData и возвращает пользователя.

    Raises:
        HTTPException: 401, если подпись неверна, данные устарели или нет пользователя.
    """
    try:
        data = safe_parse_webapp_init_data(bot_token, init_data)
    except ValueError as exc:
        raise _unauthorized("Invalid Telegram init data") from exc

    auth_date = data.auth_date
    if auth_date.tzinfo is None:
        auth_date = auth_date.replace(tzinfo=UTC)
    if (now or datetime.now(UTC)) - auth_date > max_age:
        raise _unauthorized("Telegram init data expired")
    if data.user is None:
        raise _unauthorized("Telegram init data has no user")
    return TelegramIdentity(telegram_id=data.user.id, language_code=data.user.language_code)


def resolve_identity(
    settings: ApiSettings,
    init_data: str | None,
    user_id: int | None,
) -> TelegramIdentity:
    """Определяет пользователя запроса.

    1. Есть ``X-Telegram-Init-Data``: проверяется подпись; ``user_id``, если
       передан, обязан совпадать с пользователем из подписи (иначе 403).
    2. Заголовка нет, но включён ``API_ALLOW_INSECURE_USER_ID``: берётся ``user_id``
       (только для локальной разработки).
    3. Иначе 401.

    Raises:
        HTTPException: 401/403/503 по правилам выше.
    """
    if init_data:
        if not settings.bot_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="BOT_TOKEN is not configured on the server",
            )
        identity = verify_init_data(
            init_data,
            settings.bot_token,
            timedelta(seconds=settings.init_data_max_age),
        )
        if user_id is not None and user_id != identity.telegram_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="user_id does not match Telegram init data",
            )
        return identity

    if settings.allow_insecure_user_id and user_id is not None:
        return TelegramIdentity(telegram_id=user_id)

    raise _unauthorized(f"{INIT_DATA_HEADER} header is required")
