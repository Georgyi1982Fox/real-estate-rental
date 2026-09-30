"""``/terms`` и ``/privacy``: соглашение и политика конфиденциальности (TASK-089).

``/terms`` обязательна для ботов, принимающих оплату звёздами.
Длинный документ делится на сообщения до ``MESSAGE_LIMIT`` символов;
кнопка «🏠 Главное меню» — под последним.
"""

from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bina.application.legal import LegalDoc, LegalDocument, legal_document, version_label
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.bot.texts import ui_language
from bina.infrastructure.db.models import User

# Лимит Telegram — 4096 символов; запас на разметку
MESSAGE_LIMIT = 3500


def render_messages(document: LegalDocument, language: str) -> list[str]:
    """Документ в HTML, разбитый на сообщения по разделам."""
    blocks = [
        f"<b>{escape(document.title)}</b>\n<i>{escape(version_label(language))}</i>\n\n"
        f"{escape(document.intro)}",
        *(
            f"<b>{escape(section.title)}</b>\n{escape(section.text)}"
            for section in document.sections
        ),
    ]
    messages: list[str] = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if current and len(candidate) > MESSAGE_LIMIT:
            messages.append(current)
            current = block
        else:
            current = candidate
    messages.append(current)
    return messages


async def _send(message: Message, user: User, doc: LegalDoc) -> None:
    language = ui_language(user.language)
    parts = render_messages(legal_document(doc, language), language)
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        await message.answer(part, reply_markup=with_home(None, language) if last else None)


async def cmd_terms(message: Message, user: User) -> None:
    await _send(message, user, LegalDoc.TERMS)


async def cmd_privacy(message: Message, user: User) -> None:
    await _send(message, user, LegalDoc.PRIVACY)


def create_router() -> Router:
    router = Router(name="legal")
    router.message.register(cmd_terms, Command("terms"))
    router.message.register(cmd_privacy, Command("privacy"))
    return router
