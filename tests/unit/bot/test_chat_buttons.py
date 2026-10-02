"""Кнопки «💬 N» под результатами — только объявления хозяев (TASK-111)."""

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from bina.infrastructure.bot.keyboards.callbacks import ChatAction, ChatCallback
from bina.infrastructure.bot.keyboards.listings import chat_buttons


def listing(source: str, owner: bool) -> Any:
    return SimpleNamespace(id=uuid4(), source_name=source, owner_user_id=uuid4() if owner else None)


def test_only_owner_listings_get_chat_button() -> None:
    items = [listing("ss", False), listing("owner", True), listing("owner", False)]
    rows = chat_buttons(cast(Any, items), start_index=4)
    buttons = [button for row in rows for button in row]
    assert [button.text for button in buttons] == ["💬 5"]
    data = ChatCallback.unpack(buttons[0].callback_data or "")
    assert (data.action, data.id) == (ChatAction.OPEN, items[1].id)
