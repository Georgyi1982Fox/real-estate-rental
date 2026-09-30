"""Жалобы на объявления (TASK-106).

Пользователь жалуется на объявление с причиной. Когда открытые жалобы есть от
``HIDE_AFTER`` разных людей, объявление скрывается из поиска и уведомлений до
решения модератора (TASK-110). Одна жалоба от человека на объявление; чтобы
не заваливали жалобами, не больше ``DAILY_LIMIT`` в день.
"""

from enum import StrEnum

HIDE_AFTER = 3
DAILY_LIMIT = 20


class Reason(StrEnum):
    FRAUD = "fraud"
    NOT_AVAILABLE = "not_available"
    WRONG_PRICE = "wrong_price"
    WRONG_PHOTOS = "wrong_photos"
    AGENT_AS_OWNER = "agent_as_owner"
    PREPAYMENT = "prepayment"
    OTHER = "other"


REASONS: dict[Reason, dict[str, str]] = {
    Reason.FRAUD: {"ka": "თაღლითობა", "ru": "Мошенничество", "en": "Scam"},
    Reason.NOT_AVAILABLE: {
        "ka": "ბინა უკვე გაქირავებულია",
        "ru": "Квартира уже сдана",
        "en": "Already rented",
    },
    Reason.WRONG_PRICE: {
        "ka": "ფასი არ ემთხვევა",
        "ru": "Цена не соответствует",
        "en": "Wrong price",
    },
    Reason.WRONG_PHOTOS: {
        "ka": "ფოტოები არ ემთხვევა",
        "ru": "Фото не соответствуют",
        "en": "Photos do not match",
    },
    Reason.AGENT_AS_OWNER: {
        "ka": "აგენტი მესაკუთრედ წარმოგვიდგება",
        "ru": "Агент выдаёт себя за хозяина",
        "en": "Agent posing as the owner",
    },
    Reason.PREPAYMENT: {
        "ka": "ითხოვენ წინასწარ გადახდას ნახვამდე",
        "ru": "Просят предоплату до просмотра",
        "en": "Asks for payment before a viewing",
    },
    Reason.OTHER: {"ka": "სხვა", "ru": "Другое", "en": "Other"},
}
