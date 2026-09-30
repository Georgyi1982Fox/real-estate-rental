"""/terms и /privacy в боте (TASK-089)."""

from aiogram.types import User as TelegramUser

from bina.application.legal import LegalDoc, LegalDocument, Section, legal_document
from bina.infrastructure.bot.handlers.legal import MESSAGE_LIMIT, render_messages

from .conftest import BotHarness


async def test_terms_with_home_button(harness: BotHarness) -> None:
    await harness.send("/terms")
    text = "\n".join(harness.sent_texts())
    assert "Пользовательское соглашение Bina.ai" in text
    assert "/paysupport" in text
    [[home]] = harness.last_markup().inline_keyboard
    assert home.text == "🏠 Главное меню"


async def test_privacy_in_user_language(harness: BotHarness) -> None:
    harness.telegram_user = TelegramUser(id=4242, is_bot=False, first_name="A", language_code="en")
    await harness.send("/privacy")
    text = "\n".join(harness.sent_texts())
    assert "Bina.ai Privacy Policy" in text
    assert "Политика" not in text


def test_long_documents_are_split_by_sections() -> None:
    long = "слово " * 500
    document = LegalDocument(
        title="T", intro="I", sections=tuple(Section(f"{i}.", long) for i in range(5))
    )
    parts = render_messages(document, "ru")
    assert len(parts) > 1
    assert all(len(part) <= MESSAGE_LIMIT for part in parts)
    assert "".join(parts).count("слово") == 2500


def test_real_documents_fit_telegram_limit() -> None:
    for doc in LegalDoc:
        for language in ("ru", "en", "ka"):
            parts = render_messages(legal_document(doc, language), language)
            assert all(len(part) <= 4096 for part in parts)
