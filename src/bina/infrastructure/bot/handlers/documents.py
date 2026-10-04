"""Подпись договора и акта в боте (TASK-115).

``/start sign_<токен>`` — документ файлом и кнопки «Подписать» / «Отказаться». Когда
подписали обе стороны, обоим приходит сертификат подписи. «📄 Мои документы» — в профиле.
"""

from datetime import UTC, datetime
from html import escape

import structlog
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.signing import (
    DocumentStatus,
    SignError,
    check_can_sign,
    sign_link,
)
from bina.application.use_cases.signing import SigningUseCase, SignResult
from bina.infrastructure.bot.keyboards.callbacks import SignAction, SignCallback
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import SignedDocument, User
from bina.infrastructure.db.repositories.documents import DocumentsRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from bina.infrastructure.documents.signature_certificate import render_certificate

logger = structlog.get_logger(__name__)

STATUS_ICONS = {
    DocumentStatus.PENDING: "⏳",
    DocumentStatus.SIGNED: "✅",
    DocumentStatus.DECLINED: "❌",
}


def _use_case(session: AsyncSession) -> SigningUseCase:
    return SigningUseCase(DocumentsRepository(session))


def _now() -> datetime:
    return datetime.now(UTC)


def card_text(result: SignResult, language: str) -> str:
    document = result.document
    signers = ", ".join(escape(s.name) for s in result.signers) or t(language, "doc_nobody")
    return t(
        language,
        "doc_card",
        title=escape(document.title),
        status=t(language, f"doc_status_{document.status}"),
        signers=signers,
        sha=document.sha256[:16],
    )


def sign_keyboard(result: SignResult, user: User) -> InlineKeyboardMarkup | None:
    document = result.document
    try:
        check_can_sign(document.status, document.creator_id, result.signers, user.id)
    except SignError:
        return None
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t(user.language, "doc_sign_button"),
        callback_data=SignCallback(action=SignAction.SIGN, id=document.id),
    )
    builder.button(
        text=t(user.language, "doc_decline_button"),
        callback_data=SignCallback(action=SignAction.DECLINE, id=document.id),
    )
    builder.adjust(2)
    return builder.as_markup()


def certificate(result: SignResult, language: str) -> BufferedInputFile:
    document = result.document
    content = render_certificate(
        document.title,
        document.filename,
        document.sha256,
        document.created_at,
        document.completed_at,
        result.signers,
        language,
    )
    return BufferedInputFile(content, filename=f"certificate-{document.filename}")


async def _send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except TelegramAPIError as exc:
        logger.info("Document notice not delivered", error=str(exc))


async def _invite(message: Message, bot: Bot, document: SignedDocument, language: str) -> None:
    username = (await bot.me()).username or ""
    await message.answer(t(language, "doc_invite", link=sign_link(username, document.token)))


async def open_by_token(
    message: Message, user: User, session: AsyncSession, bot: Bot, token: str
) -> None:
    """Документ по ссылке: файл, кто подписал и кнопки."""
    try:
        result = await _use_case(session).open(token)
    except SignError as exc:
        await message.answer(t(user.language, f"doc_error_{exc.code.value}"))
        return
    await _send_document(message, result, user)
    is_creator = result.document.creator_id == user.id
    if is_creator and result.document.status == DocumentStatus.PENDING:
        await _invite(message, bot, result.document, user.language)


async def _send_document(message: Message, result: SignResult, user: User) -> None:
    document = result.document
    await message.answer_document(
        BufferedInputFile(document.content, filename=document.filename),
        caption=card_text(result, user.language),
        reply_markup=sign_keyboard(result, user),
    )


async def _participants(session: AsyncSession, result: SignResult) -> list[User]:
    users = UsersRepository(session)
    ids = {result.document.creator_id, *(s.user_id for s in result.signers)}
    found = [await users.get_by_id(user_id) for user_id in ids]
    return [user for user in found if user is not None]


async def on_sign(
    callback: CallbackQuery,
    callback_data: SignCallback,
    user: User,
    session: AsyncSession,
    bot: Bot,
) -> None:
    assert callback_data.id is not None
    name = callback.from_user.full_name if callback.from_user else ""
    try:
        result = await _use_case(session).sign(callback_data.id, user, name, _now())
    except SignError as exc:
        await callback.answer(t(user.language, f"doc_error_{exc.code.value}"), show_alert=True)
        return
    # Подпись сохраняем сразу: дальше только сообщения, их сбой не должен её откатить
    await session.commit()
    await callback.answer(t(user.language, "doc_signed_you"), show_alert=True)
    message = callback.message if isinstance(callback.message, Message) else None
    if message is not None:
        await message.edit_caption(caption=card_text(result, user.language), reply_markup=None)
    document = result.document
    if result.completed:
        for person in await _participants(session, result):
            await _send(
                bot,
                person.telegram_id,
                t(person.language, "doc_completed", title=escape(document.title)),
            )
            try:
                await bot.send_document(person.telegram_id, certificate(result, person.language))
            except TelegramAPIError as exc:
                logger.info("Certificate not delivered", error=str(exc))
        return
    if document.creator_id == user.id:
        if message is not None:
            await _invite(message, bot, document, user.language)
        return
    creator = await UsersRepository(session).get_by_id(document.creator_id)
    if creator is not None:
        username = (await bot.me()).username or ""
        await _send(
            bot,
            creator.telegram_id,
            t(
                creator.language,
                "doc_signed_other",
                name=escape(name or str(user.telegram_id)),
                title=escape(document.title),
                link=sign_link(username, document.token),
            ),
        )


async def on_decline(
    callback: CallbackQuery,
    callback_data: SignCallback,
    user: User,
    session: AsyncSession,
    bot: Bot,
) -> None:
    assert callback_data.id is not None
    try:
        result = await _use_case(session).decline(callback_data.id, user)
    except SignError as exc:
        await callback.answer(t(user.language, f"doc_error_{exc.code.value}"), show_alert=True)
        return
    await session.commit()
    await callback.answer(t(user.language, "doc_declined_you"), show_alert=True)
    if isinstance(callback.message, Message):
        await callback.message.edit_caption(
            caption=card_text(result, user.language), reply_markup=None
        )
    name = escape(callback.from_user.full_name if callback.from_user else "")
    for person in await _participants(session, result):
        if person.id != user.id:
            await _send(
                bot,
                person.telegram_id,
                t(
                    person.language,
                    "doc_declined_other",
                    name=name,
                    title=escape(result.document.title),
                ),
            )


async def on_open(
    callback: CallbackQuery, callback_data: SignCallback, user: User, session: AsyncSession
) -> None:
    """Свой документ ещё раз (и сертификат, если подписан)."""
    assert callback_data.id is not None
    try:
        result = await _use_case(session).participant(callback_data.id, user.id)
    except SignError as exc:
        await callback.answer(t(user.language, f"doc_error_{exc.code.value}"), show_alert=True)
        return
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await _send_document(callback.message, result, user)
    if result.completed:
        await callback.message.answer_document(certificate(result, user.language))


async def on_list(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """«📄 Мои документы»: список с кнопкой на каждый."""
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    documents = await _use_case(session).mine(user.id)
    if not documents:
        await callback.message.answer(t(user.language, "my_docs_empty"))
        return
    builder = InlineKeyboardBuilder()
    for document in documents:
        icon = STATUS_ICONS.get(DocumentStatus(document.status), "📄")
        builder.button(
            text=f"{icon} {document.title[:40]} · {document.created_at:%d.%m.%Y}",
            callback_data=SignCallback(action=SignAction.OPEN, id=document.id),
        )
    builder.adjust(1)
    await callback.message.answer(
        t(user.language, "my_docs_header"),
        reply_markup=with_home(builder.as_markup(), user.language),
    )


def create_router() -> Router:
    router = Router(name="documents")
    router.callback_query.register(on_sign, SignCallback.filter(F.action == SignAction.SIGN))
    router.callback_query.register(on_decline, SignCallback.filter(F.action == SignAction.DECLINE))
    router.callback_query.register(on_open, SignCallback.filter(F.action == SignAction.OPEN))
    router.callback_query.register(on_list, SignCallback.filter(F.action == SignAction.LIST))
    return router
