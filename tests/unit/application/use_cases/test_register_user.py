from unittest.mock import AsyncMock, MagicMock

import pytest

from bina.application.use_cases.register_user import (
    DEFAULT_LANGUAGE,
    RegisterUserUseCase,
    normalize_language,
)
from bina.infrastructure.db.models import User


@pytest.fixture
def users_repository() -> AsyncMock:
    """Мок репозитория пользователей."""
    return AsyncMock()


@pytest.mark.parametrize(
    ("language_code", "expected"),
    [
        ("ru", "ru"),
        ("en", "en"),
        ("en-US", "en"),
        ("KA", "ka"),
        ("de", DEFAULT_LANGUAGE),
        ("", DEFAULT_LANGUAGE),
        (None, DEFAULT_LANGUAGE),
    ],
)
def test_normalize_language(language_code: str | None, expected: str) -> None:
    """Коды языков Telegram приводятся к поддерживаемым."""
    assert normalize_language(language_code) == expected


async def test_returns_existing_user(users_repository: AsyncMock) -> None:
    """Существующий пользователь возвращается без создания."""
    user = MagicMock(spec=User)
    users_repository.get_by_telegram_id.return_value = user

    result = await RegisterUserUseCase(users_repository).execute(42, "en")

    assert result.user is user
    assert result.created is False
    users_repository.get_by_telegram_id.assert_awaited_once_with(42)
    users_repository.create.assert_not_awaited()


async def test_creates_new_user_with_normalized_language(users_repository: AsyncMock) -> None:
    """Новый пользователь создаётся с нормализованным языком."""
    user = MagicMock(spec=User)
    users_repository.get_by_telegram_id.return_value = None
    users_repository.create.return_value = user

    result = await RegisterUserUseCase(users_repository).execute(42, "en-GB")

    assert result.user is user
    assert result.created is True
    users_repository.create.assert_awaited_once_with(42, "en")
