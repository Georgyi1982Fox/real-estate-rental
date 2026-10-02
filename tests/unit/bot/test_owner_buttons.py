"""Кнопки «Моих объявлений»: номер — только когда объявлений несколько."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from bina.infrastructure.bot.handlers.owner import list_keyboard
from bina.infrastructure.db.models import ListingStatus


def listing() -> Any:
    return SimpleNamespace(
        id=uuid4(),
        status=ListingStatus.ACTIVE,
        hidden_at=None,
        is_verified=False,
        promoted_until=datetime(2020, 1, 1, tzinfo=UTC),
    )


def labels(count: int) -> list[str]:
    markup = list_keyboard("ru", cast(Any, [listing() for _ in range(count)]))
    return [button.text for row in markup.inline_keyboard for button in row]


def test_single_listing_buttons_have_no_number() -> None:
    assert labels(1)[:4] == ["⚪ Снять", "💰 Цена", "🔥 Топ", "✅ Проверка"]


def test_several_listings_buttons_are_numbered() -> None:
    texts = labels(2)
    assert texts[:4] == ["⚪ Снять 1", "💰 Цена 1", "🔥 Топ 1", "✅ Проверка 1"]
    assert texts[4:8] == ["⚪ Снять 2", "💰 Цена 2", "🔥 Топ 2", "✅ Проверка 2"]
