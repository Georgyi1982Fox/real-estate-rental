from dataclasses import dataclass

import structlog

from bina.application.repositories.users import IUsersRepository
from bina.infrastructure.db.models import User

logger = structlog.get_logger(__name__)

SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"ru", "en", "ka"})
DEFAULT_LANGUAGE = "ru"


def normalize_language(language_code: str | None) -> str:
    """Приводит код языка Telegram (например, ``en-US``) к поддерживаемому языку."""
    if not language_code:
        return DEFAULT_LANGUAGE
    base = language_code.split("-", 1)[0].lower()
    return base if base in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


@dataclass(frozen=True, slots=True)
class RegisterUserResult:
    """Результат регистрации пользователя."""

    user: User
    created: bool


class RegisterUserUseCase:
    """Use-case: найти пользователя по Telegram ID или зарегистрировать нового."""

    def __init__(self, users_repository: IUsersRepository) -> None:
        self.users_repository = users_repository

    async def execute(
        self,
        telegram_id: int,
        language_code: str | None = None,
    ) -> RegisterUserResult:
        """Возвращает существующего пользователя или создаёт нового.

        Язык берётся из ``language_code`` только при создании: выбор
        пользователя в профиле не перезаписывается.
        """
        user = await self.users_repository.get_by_telegram_id(telegram_id)
        if user is not None:
            return RegisterUserResult(user=user, created=False)

        language = normalize_language(language_code)
        user = await self.users_repository.create(telegram_id, language)
        logger.info("User registered", telegram_id=telegram_id, language=language)
        return RegisterUserResult(user=user, created=True)
