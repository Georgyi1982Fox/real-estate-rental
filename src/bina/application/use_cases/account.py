"""Свои данные: выгрузить и удалить (TASK-059, TASK-060).

Выгрузка — JSON со всем, что хранится о человеке. Удаление — сразу и без возврата:
избранное, поиски, уведомления, напоминания, переписка, объявления с фото, кабинет
агентства, жалобы, заявки «я собственник». Платежи остаются для бухгалтерии, но уже без
Telegram ID — ни с кем не связаны.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, Protocol

import structlog

from bina.application.ports.photo_storage import IPhotoStorage
from bina.infrastructure.db.models import User

logger = structlog.get_logger(__name__)

EXPORT_VERSION = 1


class IAccountRepository(Protocol):
    async def export(self, user: User) -> dict[str, Any]: ...

    async def erase(self, user: User, now: datetime) -> list[str]: ...


class AccountUseCase:
    def __init__(self, repository: IAccountRepository, storage: IPhotoStorage) -> None:
        self._repository = repository
        self._storage = storage

    async def export(self, user: User, now: datetime) -> dict[str, Any]:
        data = await self._repository.export(user)
        return {"service": "Bina.ai", "version": EXPORT_VERSION, "exported_at": now.isoformat()} | (
            data
        )

    async def erase(self, user: User, now: datetime, commit: Callable[[], Awaitable[None]]) -> None:
        """Удалить всё; фото стираются с диска только после сохранения в базе."""
        files = await self._repository.erase(user, now)
        await commit()
        for url in files:
            try:
                self._storage.delete(url)
            except OSError as exc:
                logger.warning("Photo of erased account not deleted", url=url, error=str(exc))
        logger.info("Account erased", user_id=str(user.id), files=len(files))
