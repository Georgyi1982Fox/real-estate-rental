"""Электронная подпись и хранение документов (TASK-115).

Договор аренды или акт приёмки сохраняется у нас (файл и его отпечаток SHA-256). Создатель
пересылает второй стороне ссылку на бота; каждая сторона открывает документ в боте и
нажимает «Подписать» — согласие подтверждается её аккаунтом Telegram. Когда подписали оба,
обоим приходит сертификат подписи: кто, когда и какой именно файл подписал.

Это простая электронная подпись: она фиксирует согласие сторон, а отпечаток позволяет
проверить, что файл после подписи не меняли.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

SIGN_PREFIX = "sign_"
# Подписывают двое: создатель и вторая сторона
SIGNERS = 2
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{8,40}$")


class DocumentKind(StrEnum):
    CONTRACT = "contract"
    ACCEPTANCE = "acceptance"


class DocumentStatus(StrEnum):
    PENDING = "pending"  # ждёт подписей
    SIGNED = "signed"  # подписали обе стороны
    DECLINED = "declined"  # кто-то отказался


class SignErrorCode(StrEnum):
    NOT_FOUND = "not_found"
    CLOSED = "closed"  # уже подписан обеими сторонами или отклонён
    ALREADY_SIGNED = "already_signed"
    TAKEN = "taken"  # вторая сторона уже подписала — третий не может


class SignError(Exception):
    def __init__(self, code: SignErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True, slots=True)
class Signer:
    user_id: UUID
    name: str
    telegram_id: int
    signed_at: datetime


def fingerprint(content: bytes) -> str:
    """Отпечаток файла: SHA-256 в шестнадцатеричном виде."""
    return hashlib.sha256(content).hexdigest()


def sign_link(bot_username: str, token: str) -> str:
    return f"https://t.me/{bot_username}?start={SIGN_PREFIX}{token}"


def token_from_start(payload: str | None) -> str | None:
    """Токен документа из ``/start sign_<токен>``."""
    if not payload or not payload.startswith(SIGN_PREFIX):
        return None
    token = payload.removeprefix(SIGN_PREFIX)
    return token if _TOKEN_RE.match(token) else None


def check_can_sign(status: str, creator_id: UUID, signers: list[Signer], user_id: UUID) -> None:
    """Может ли ``user_id`` подписать документ; иначе :class:`SignError`."""
    if status != DocumentStatus.PENDING:
        raise SignError(SignErrorCode.CLOSED)
    if any(signer.user_id == user_id for signer in signers):
        raise SignError(SignErrorCode.ALREADY_SIGNED)
    others = [s for s in signers if s.user_id != creator_id]
    if user_id != creator_id and others:
        raise SignError(SignErrorCode.TAKEN)
