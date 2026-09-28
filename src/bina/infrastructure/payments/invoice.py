"""Счёт на оплату подписки звёздами Telegram (TASK-027).

Общий для бота (``send_invoice``) и Mini App (``create_invoice_link`` →
``Telegram.WebApp.openInvoice``).
"""

from aiogram import Bot
from aiogram.types import LabeledPrice

from bina.application.subscriptions import STARS_CURRENCY, Plan

_TEXTS: dict[str, dict[str, str]] = {
    "ru": {
        "title": "Bina.ai Premium",
        "description": (
            "Premium на {days} дн.: избранное без ограничений и до 20 сохранённых поисков "
            "с уведомлениями о новых квартирах."
        ),
        "label": "Premium на {days} дн.",
    },
    "en": {
        "title": "Bina.ai Premium",
        "description": (
            "Premium for {days} days: unlimited favorites and up to 20 saved searches "
            "with alerts about new apartments."
        ),
        "label": "Premium for {days} days",
    },
}


def _texts(language: str) -> dict[str, str]:
    return _TEXTS.get(language, _TEXTS["en"])


def invoice_title(language: str) -> str:
    """Заголовок счёта."""
    return _texts(language)["title"]


def invoice_description(plan: Plan, language: str) -> str:
    """Описание счёта (до 255 символов)."""
    return _texts(language)["description"].format(days=plan.days)


def invoice_prices(plan: Plan, language: str) -> list[LabeledPrice]:
    """Цена в звёздах: для XTR ровно одна позиция."""
    return [
        LabeledPrice(
            label=_texts(language)["label"].format(days=plan.days), amount=plan.price_stars
        )
    ]


async def create_invoice_link(bot: Bot, plan: Plan, language: str) -> str:
    """Ссылка на счёт для ``Telegram.WebApp.openInvoice``."""
    return await bot.create_invoice_link(
        title=invoice_title(language),
        description=invoice_description(plan, language),
        payload=plan.invoice_payload,
        currency=STARS_CURRENCY,
        prices=invoice_prices(plan, language),
    )
