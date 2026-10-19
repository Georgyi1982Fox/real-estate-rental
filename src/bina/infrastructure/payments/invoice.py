"""Счёт на оплату подписки звёздами Telegram (TASK-027).

Общий для бота (``send_invoice``) и Mini App (``create_invoice_link`` →
``Telegram.WebApp.openInvoice``).
"""

from typing import Any

from aiogram import Bot
from aiogram.types import LabeledPrice

from bina.application.hotel_promotion import hotel_promotion_payload, hotel_promotion_price
from bina.application.promotion import PROMOTION_DAYS
from bina.application.subscriptions import STARS_CURRENCY, Plan
from bina.infrastructure.db.models import Hotel

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


# ---------------------------------------------------------------- «🔥 Топ» гостиницы (TASK-120)

_HOTEL_PROMO: dict[str, dict[str, str]] = {
    "ka": {
        "title": "🔥 ტოპი: {name}",
        "description": (
            "{days} დღე თქვენი ობიექტი პირველია განყოფილებაში «სასტუმროები» ნიშნით «🔥 ტოპი»."
        ),
        "label": "ტოპი {days} დღით",
    },
    "ru": {
        "title": "🔥 Топ: {name}",
        "description": ("{days} дней ваш объект первым в разделе «Гостиницы» со значком «🔥 Топ»."),
        "label": "Топ на {days} дн.",
    },
    "en": {
        "title": "🔥 Top: {name}",
        "description": "Your property is first in the Hotels section with a «🔥 Top» badge "
        "for {days} days.",
        "label": "Top for {days} days",
    },
}
# Ограничения Telegram для счёта
_TITLE_MAX = 32


def hotel_promotion_invoice(hotel: Hotel, language: str) -> dict[str, Any]:
    """Поля счёта за «Топ» гостиницы: для ``send_invoice`` и ``create_invoice_link``."""
    texts = _HOTEL_PROMO.get(language, _HOTEL_PROMO["en"])
    title = texts["title"].format(name=hotel.name)
    if len(title) > _TITLE_MAX:
        title = title[: _TITLE_MAX - 1].rstrip() + "…"
    return {
        "title": title,
        "description": texts["description"].format(days=PROMOTION_DAYS),
        "payload": hotel_promotion_payload(hotel.id),
        "currency": STARS_CURRENCY,
        "prices": [
            LabeledPrice(
                label=texts["label"].format(days=PROMOTION_DAYS), amount=hotel_promotion_price()
            )
        ],
    }


async def create_hotel_promotion_link(bot: Bot, hotel: Hotel, language: str) -> str:
    """Ссылка на счёт за «Топ» для ``Telegram.WebApp.openInvoice``."""
    return await bot.create_invoice_link(**hotel_promotion_invoice(hotel, language))
