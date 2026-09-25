import structlog
from aiogram import Router
from aiogram.types import ErrorEvent

from bina.application.use_cases.register_user import DEFAULT_LANGUAGE
from bina.infrastructure.bot.texts import t

logger = structlog.get_logger(__name__)


async def on_error(event: ErrorEvent, user_language: str = DEFAULT_LANGUAGE) -> None:
    """Логирует необработанную ошибку и вежливо сообщает о ней пользователю.

    Транзакция к этому моменту уже откатана :class:`DbSessionMiddleware`, поэтому
    язык берётся из строки ``user_language``, а не из ORM-объекта ``user``.
    """
    logger.exception(
        "Unhandled bot error",
        update_id=event.update.update_id,
        exc_info=event.exception,
    )
    text = t(user_language, "error")
    update = event.update
    try:
        if update.callback_query is not None:
            await update.callback_query.answer(text, show_alert=True)
        elif update.message is not None:
            await update.message.answer(text)
    except Exception:  # noqa: BLE001 - уведомление об ошибке не должно порождать новую
        logger.warning("Failed to notify user about error", update_id=update.update_id)


def create_router() -> Router:
    """Создаёт роутер раздела «errors» (новый экземпляр на каждый Dispatcher)."""
    router = Router(name="errors")
    router.errors.register(on_error)
    return router
