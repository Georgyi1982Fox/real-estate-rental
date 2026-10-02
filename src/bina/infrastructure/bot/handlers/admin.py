"""``/admin``: минимальная админка владельца (TASK-110).

Доступна Telegram ID из ``ADMIN_TELEGRAM_IDS`` и пользователям с ролью admin;
остальным бот отвечает как на неизвестную команду.

- Статистика: пользователи, Premium, звёзды, объявления по источникам, районы.
- Очередь жалоб: объявление, число жалоб и причины; «Скрыть» или «Вернуть в поиск».
"""

from collections import Counter
from datetime import UTC, datetime
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.complaints import REASONS, Reason
from bina.infrastructure.bot.keyboards.callbacks import AdminAction, AdminCallback
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import t, ui_language
from bina.infrastructure.db.models import User
from bina.infrastructure.db.models.users import UserRole
from bina.infrastructure.db.repositories.admin import AdminRepository, AdminStats, ComplaintCase

QUEUE_SIZE = 5
TITLE_LENGTH = 80


def is_admin(user: User, settings: BotSettings) -> bool:
    return user.telegram_id in settings.admin_ids or user.role == UserRole.ADMIN


def render_stats(language: str, stats: AdminStats) -> str:
    def lines(rows: list[tuple[str, int]]) -> str:
        return "\n".join(f"• {escape(name)}: {count}" for name, count in rows) or "—"

    return t(
        language,
        "admin_stats",
        users=stats.users,
        users_week=stats.users_week,
        premium=stats.premium,
        stars_month=int(stats.stars_month),
        payments_month=stats.payments_month,
        stars_total=int(stats.stars_total),
        sources=lines(stats.sources),
        hidden=stats.hidden,
        complaints=stats.open_complaints,
        districts=lines(stats.districts),
    )


def stats_keyboard(language: str, complaints: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t(language, "admin_complaints", count=complaints),
        callback_data=AdminCallback(action=AdminAction.COMPLAINTS),
    )
    builder.button(
        text=t(language, "admin_refresh"), callback_data=AdminCallback(action=AdminAction.STATS)
    )
    builder.adjust(1)
    return builder.as_markup()


def render_case(language: str, case: ComplaintCase) -> str:
    lang = ui_language(language)
    counts = Counter(case.reasons)
    reasons = ", ".join(
        f"{REASONS[Reason(code)][lang] if code in Reason else code} ({count})"
        for code, count in counts.most_common()
    )
    text = t(
        language,
        "admin_case",
        title=escape(case.title[:TITLE_LENGTH]),
        source=escape(case.source),
        count=case.complaints,
        hidden=t(language, "admin_case_hidden") if case.hidden else "",
        reasons=reasons,
    )
    for comment in case.comments[:3]:
        text += f"\n💬 {escape(comment)}"
    if case.url:
        text += f"\n{escape(case.url)}"
    return text


def case_keyboard(language: str, case: ComplaintCase) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t(language, "admin_hide"),
        callback_data=AdminCallback(action=AdminAction.HIDE, listing=case.listing_id),
    )
    builder.button(
        text=t(language, "admin_restore"),
        callback_data=AdminCallback(action=AdminAction.RESTORE, listing=case.listing_id),
    )
    builder.adjust(2)
    return builder.as_markup()


async def _send_stats(message: Message, user: User, session: AsyncSession) -> None:
    stats = await AdminRepository(session).stats(datetime.now(UTC))
    await message.answer(
        render_stats(user.language, stats),
        reply_markup=stats_keyboard(user.language, stats.open_complaints),
    )


async def cmd_admin(
    message: Message, user: User, session: AsyncSession, settings: BotSettings
) -> None:
    if not is_admin(user, settings):
        await message.answer(t(user.language, "unknown"))
        return
    await _send_stats(message, user, session)


async def on_admin(
    callback: CallbackQuery,
    callback_data: AdminCallback,
    user: User,
    session: AsyncSession,
    settings: BotSettings,
) -> None:
    message = callback.message
    if not is_admin(user, settings) or not isinstance(message, Message):
        await callback.answer()
        return
    repository = AdminRepository(session)
    if callback_data.action == AdminAction.STATS:
        await _send_stats(message, user, session)
    elif callback_data.action == AdminAction.COMPLAINTS:
        cases = await repository.complaint_queue(QUEUE_SIZE)
        if not cases:
            await message.answer(t(user.language, "admin_no_complaints"))
        for case in cases:
            await message.answer(
                render_case(user.language, case),
                reply_markup=case_keyboard(user.language, case),
                disable_web_page_preview=True,
            )
    elif callback_data.listing is not None:
        if callback_data.action == AdminAction.HIDE:
            await repository.hide(callback_data.listing)
            await message.answer(t(user.language, "admin_hidden"))
        else:
            await repository.restore(callback_data.listing)
            await message.answer(t(user.language, "admin_restored"))
    await callback.answer()


def create_router() -> Router:
    router = Router(name="admin")
    router.message.register(cmd_admin, Command("admin"))
    # Проверку собственника (VERIFY_*) обрабатывает handlers/promotion.py
    actions = {AdminAction.STATS, AdminAction.COMPLAINTS, AdminAction.HIDE, AdminAction.RESTORE}
    router.callback_query.register(on_admin, AdminCallback.filter(F.action.in_(actions)))
    return router
