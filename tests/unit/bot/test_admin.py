"""/admin (TASK-110): только владельцу; статистика и очередь жалоб."""

from uuid import uuid4

import pytest

from bina.infrastructure.bot.keyboards.callbacks import AdminAction, AdminCallback
from bina.infrastructure.bot.settings import BotConfigError, BotSettings
from bina.infrastructure.db.repositories.admin import ComplaintCase
from tests.support.telegram import CHAT_ID, TOKEN

from .conftest import BotHarness


@pytest.fixture
def settings() -> BotSettings:
    return BotSettings(token=TOKEN, page_size=3, admin_ids=(CHAT_ID,))


async def test_stats_for_owner_only(harness: BotHarness) -> None:
    await harness.send("/admin", id=12345)
    assert "Не понял" in harness.last_text()

    await harness.send("/admin")
    text = harness.last_text()
    assert "Пользователей: 2" in text
    assert "• myhome: 626" in text
    assert "250 за 30 дней" in text
    assert "• Ваке: 120" in text


async def test_complaint_queue(harness: BotHarness) -> None:
    case = ComplaintCase(
        listing_id=uuid4(),
        title="Квартира <в Ваке>",
        url="https://ss.ge/1",
        source="ss",
        complaints=3,
        reasons=["fraud", "fraud", "prepayment"],
        comments=["просят деньги до просмотра"],
        hidden=True,
    )
    harness.store.cases.append(case)
    await harness.send("/start")
    await harness.press(AdminCallback(action=AdminAction.COMPLAINTS).pack())
    text = harness.last_text()
    assert "Квартира &lt;в Ваке&gt;" in text
    assert "жалоб: 3 · уже скрыто" in text
    assert "Мошенничество (2), Просят предоплату до просмотра (1)" in text
    assert "💬 просят деньги до просмотра" in text

    await harness.press(AdminCallback(action=AdminAction.RESTORE, listing=case.listing_id).pack())
    await harness.press(AdminCallback(action=AdminAction.HIDE, listing=case.listing_id).pack())
    assert harness.store.admin_actions == [
        ("restore", case.listing_id),
        ("hide", case.listing_id),
    ]


async def test_empty_queue(harness: BotHarness) -> None:
    await harness.send("/start")
    await harness.press(AdminCallback(action=AdminAction.COMPLAINTS).pack())
    assert harness.last_text() == "Открытых жалоб нет."


def test_admin_ids_setting() -> None:
    base = {"BOT_TOKEN": TOKEN}
    assert BotSettings.from_env(base).admin_ids == ()
    assert BotSettings.from_env({**base, "ADMIN_TELEGRAM_IDS": "123, 456"}).admin_ids == (
        123,
        456,
    )
    with pytest.raises(BotConfigError):
        BotSettings.from_env({**base, "ADMIN_TELEGRAM_IDS": "me"})
