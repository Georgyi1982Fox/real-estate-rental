"""Счёт на оплату подписки звёздами Telegram (TASK-027).

Общий для бота (``send_invoice``) и Mini App (``create_invoice_link`` →
``Telegram.WebApp.openInvoice``).
"""

from aiogram import Bot
from aiogram.types import LabeledPrice

from bina.application.subscriptions import STARS_CURRENCY, Plan

_TEXTS: dict[str, dict[str, str]] = {
    "ka": {
        "title": "Bina.ai Premium",
        "description": (
            "Premium {days} დღით: 20-მდე შენახული ძებნა, ახალი ბინები მაშინვე, "
            "შეტყობინებები ფასის შემცირებისას."
        ),
        "label": "Premium {days} დღით",
    },
    "ru": {
        "title": "Bina.ai Premium",
        "description": (
            "Premium на {days} дн.: до 20 сохранённых поисков, новые квартиры сразу, "
            "уведомления о снижении цены."
        ),
        "label": "Premium на {days} дн.",
    },
    "en": {
        "title": "Bina.ai Premium",
        "description": (
            "Premium for {days} days: up to 20 saved searches, new apartments right away, "
            "price drop alerts."
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


def invoice_prices(plan: Plan, language: str, price: int | None = None) -> list[LabeledPrice]:
    """Цена в звёздах: для XTR ровно одна позиция; ``price`` — со скидкой (TASK-108)."""
    return [
        LabeledPrice(
            label=_texts(language)["label"].format(days=plan.days),
            amount=plan.price_stars if price is None else price,
        )
    ]


async def create_invoice_link(bot: Bot, plan: Plan, language: str, price: int | None = None) -> str:
    """Ссылка на счёт для ``Telegram.WebApp.openInvoice``."""
    return await bot.create_invoice_link(
        title=invoice_title(language),
        description=invoice_description(plan, language),
        payload=plan.invoice_payload,
        currency=STARS_CURRENCY,
        prices=invoice_prices(plan, language, price),
    )
