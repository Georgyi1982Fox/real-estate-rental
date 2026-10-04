"""Правила подписи документов (TASK-115)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bina.application.signing import (
    Signer,
    SignError,
    SignErrorCode,
    check_can_sign,
    fingerprint,
    sign_link,
    token_from_start,
)

CREATOR, OTHER, THIRD = uuid4(), uuid4(), uuid4()


def signer(user_id: object) -> Signer:
    return Signer(user_id, "Name", 1, datetime.now(UTC))  # type: ignore[arg-type]


def test_two_parties_in_any_order() -> None:
    check_can_sign("pending", CREATOR, [], OTHER)  # вторая сторона может первой
    check_can_sign("pending", CREATOR, [signer(OTHER)], CREATOR)
    with pytest.raises(SignError) as taken:
        check_can_sign("pending", CREATOR, [signer(OTHER)], THIRD)
    assert taken.value.code is SignErrorCode.TAKEN, "третий подписать не может"
    with pytest.raises(SignError) as again:
        check_can_sign("pending", CREATOR, [signer(CREATOR)], CREATOR)
    assert again.value.code is SignErrorCode.ALREADY_SIGNED
    with pytest.raises(SignError) as closed:
        check_can_sign("declined", CREATOR, [], OTHER)
    assert closed.value.code is SignErrorCode.CLOSED


def test_link_and_fingerprint() -> None:
    link = sign_link("bina_bot", "AbC-123_xyzAbC-123_xy")
    assert link == "https://t.me/bina_bot?start=sign_AbC-123_xyzAbC-123_xy"
    assert token_from_start("sign_AbC-123_xyzAbC-123_xy") == "AbC-123_xyzAbC-123_xy"
    assert token_from_start("sign_<script>") is None and token_from_start("l_abc") is None
    assert fingerprint(b"pdf") == fingerprint(b"pdf") != fingerprint(b"pdf!")
    assert len(fingerprint(b"")) == 64
