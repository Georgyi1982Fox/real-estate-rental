"""Подробный разбор риска объявления для Premium (TASK-094).

Значок и коды причин видят все (TASK-011, FRONTEND-012). Premium получает
объяснение каждой причины и список «что проверить до встречи» на языке
пользователя. Тексты заготовлены: запросов к AI нет.
"""

from dataclasses import dataclass

from bina.application.fraud import FraudLevel, fraud_level
from bina.application.ports.fraud import REASONS


@dataclass(frozen=True, slots=True)
class ReasonText:
    """Причина: короткое название и объяснение."""

    title: str
    explanation: str
    # Что сделать или спросить именно из-за этой причины
    check: str


@dataclass(frozen=True, slots=True)
class RiskReport:
    """Разбор риска."""

    level: FraudLevel
    reasons: list[tuple[str, ReasonText]]
    checklist: list[str]


_REASONS: dict[str, dict[str, ReasonText]] = {
    "ru": {
        "prepayment": ReasonText(
            "Просят предоплату",
            "В объявлении просят перевести деньги до просмотра или «забронировать» квартиру.",
            "Не переводите деньги до просмотра и подписания договора.",
        ),
        "off_platform": ReasonText(
            "Уводят в переписку",
            "Автор избегает звонков и просмотров, просит писать только в мессенджер или на почту.",
            "Попросите созвониться и показать квартиру по видео или вживую.",
        ),
        "urgency": ReasonText(
            "Торопят",
            "Давят сроком: «только сегодня», «много желающих», «решайте сейчас».",
            "Не принимайте решение в спешке — честный хозяин подождёт день.",
        ),
        "too_good": ReasonText(
            "Слишком хорошо для такой цены",
            "Большая или элитная квартира почти даром — так часто заманивают.",
            "Сравните с похожими квартирами района и спросите, почему так дёшево.",
        ),
        "vague": ReasonText(
            "Мало подробностей",
            "Нет адреса и деталей, текст подходит к любой квартире.",
            "Спросите точный адрес, этаж и попросите свежие фото.",
        ),
        "owner_abroad": ReasonText(
            "«Хозяин за границей»",
            "Посмотреть квартиру нельзя, ключи обещают прислать после оплаты.",
            "Не соглашайтесь без просмотра: это самая частая схема обмана.",
        ),
        "price_far_below_market": ReasonText(
            "Цена намного ниже рынка",
            "Цена за м² сильно ниже средней по району.",
            "Уточните, что входит в цену, и нет ли скрытых платежей.",
        ),
        "no_photos": ReasonText(
            "Нет фотографий",
            "В объявлении нет ни одного фото квартиры.",
            "Попросите фото или видео до встречи.",
        ),
    },
    "en": {
        "prepayment": ReasonText(
            "Asks for prepayment",
            "The listing asks to send money before a viewing or to 'reserve' the flat.",
            "Do not send money before the viewing and a signed contract.",
        ),
        "off_platform": ReasonText(
            "Avoids calls and viewings",
            "The author avoids calls and viewings and wants to talk only in a messenger or e-mail.",
            "Ask for a call and a viewing, in person or by video.",
        ),
        "urgency": ReasonText(
            "Pressure to hurry",
            "Deadlines like 'today only', 'many people want it', 'decide now'.",
            "Don't decide in a hurry: an honest owner will wait a day.",
        ),
        "too_good": ReasonText(
            "Too good for the price",
            "A large or luxury flat almost for free is a common bait.",
            "Compare with similar flats in the district and ask why it is so cheap.",
        ),
        "vague": ReasonText(
            "Few details",
            "No address or details; the text would fit any flat.",
            "Ask for the exact address and floor and for recent photos.",
        ),
        "owner_abroad": ReasonText(
            "'The owner is abroad'",
            "No viewing is possible; keys are promised after payment.",
            "Never agree without a viewing: this is the most common scam.",
        ),
        "price_far_below_market": ReasonText(
            "Price far below the market",
            "The price per m² is much lower than the district average.",
            "Ask what the price includes and whether there are hidden fees.",
        ),
        "no_photos": ReasonText(
            "No photos",
            "The listing has no photos of the flat.",
            "Ask for photos or a video before meeting.",
        ),
    },
    "ka": {
        "prepayment": ReasonText(
            "ითხოვენ წინასწარ გადახდას",
            "განცხადებაში ითხოვენ თანხის გადარიცხვას ნახვამდე ან ბინის „დაჯავშნას“.",
            "არ გადარიცხოთ თანხა ნახვამდე და ხელშეკრულების გაფორმებამდე.",
        ),
        "off_platform": ReasonText(
            "თავს არიდებენ ზარს და ნახვას",
            "ავტორი არ რეკავს და არ აჩვენებს ბინას, წერს მხოლოდ მესენჯერში ან ფოსტით.",
            "მოითხოვეთ ზარი და ბინის ნახვა — პირადად ან ვიდეოთი.",
        ),
        "urgency": ReasonText(
            "გაჩქარებენ",
            "„მხოლოდ დღეს“, „ბევრი მსურველია“, „ახლავე გადაწყვიტეთ“.",
            "ნუ მიიღებთ გადაწყვეტილებას ჩქარა — პატიოსანი მეპატრონე ერთ დღეს დაიცდის.",
        ),
        "too_good": ReasonText(
            "ზედმეტად კარგია ამ ფასად",
            "დიდი ან ძვირადღირებული ბინა თითქმის უფასოდ — ხშირი მახეა.",
            "შეადარეთ უბნის მსგავს ბინებს და ჰკითხეთ, რატომ არის ასე იაფი.",
        ),
        "vague": ReasonText(
            "ცოტა დეტალი",
            "არ არის მისამართი და დეტალები, ტექსტი ნებისმიერ ბინას მიესადაგება.",
            "იკითხეთ ზუსტი მისამართი, სართული და სთხოვეთ ახალი ფოტოები.",
        ),
        "owner_abroad": ReasonText(
            "„მეპატრონე საზღვარგარეთაა“",
            "ბინის ნახვა შეუძლებელია, გასაღებს გადახდის შემდეგ გპირდებიან.",
            "არასოდეს დათანხმდეთ ნახვის გარეშე — ეს ყველაზე გავრცელებული თაღლითობაა.",
        ),
        "price_far_below_market": ReasonText(
            "ფასი ბაზარზე გაცილებით დაბალია",
            "კვადრატული მეტრის ფასი უბნის საშუალოზე ბევრად დაბალია.",
            "დააზუსტეთ, რას მოიცავს ფასი და ხომ არ არის დამალული გადასახადები.",
        ),
        "no_photos": ReasonText(
            "ფოტოები არ არის",
            "განცხადებაში ბინის არც ერთი ფოტო არ არის.",
            "სთხოვეთ ფოტოები ან ვიდეო შეხვედრამდე.",
        ),
    },
}

# Общие советы — в конце списка для любого объявления
_GENERAL: dict[str, list[str]] = {
    "ru": [
        "Посмотрите квартиру вживую до любых платежей.",
        "Попросите выписку из реестра (Публичный реестр) и паспорт собственника.",
        "Подпишите договор: сумма, депозит, срок, коммунальные платежи.",
        "Платите депозит при подписании, а не заранее; сохраните расписку или перевод.",
    ],
    "en": [
        "See the flat in person before any payment.",
        "Ask for the Public Registry extract and the owner's ID.",
        "Sign a contract: rent, deposit, term, utilities.",
        "Pay the deposit at signing, not in advance; keep a receipt or bank record.",
    ],
    "ka": [
        "ნახეთ ბინა პირადად ნებისმიერ გადახდამდე.",
        "მოითხოვეთ საჯარო რეესტრის ამონაწერი და მესაკუთრის პირადობა.",
        "გააფორმეთ ხელშეკრულება: ფასი, დეპოზიტი, ვადა, კომუნალური გადასახადები.",
        "დეპოზიტი გადაიხადეთ ხელმოწერისას და არა წინასწარ; შეინახეთ ქვითარი.",
    ],
}

assert all(set(texts) == REASONS for texts in _REASONS.values()), "тексты для всех причин"


def risk_report(score: int, reasons: list[str], language: str) -> RiskReport:
    """Разбор риска на языке пользователя (неизвестный язык — английский)."""
    lang = language if language in _REASONS else "en"
    texts = _REASONS[lang]
    known = [(code, texts[code]) for code in dict.fromkeys(reasons) if code in texts]
    checklist = [text.check for _, text in known] + _GENERAL[lang]
    return RiskReport(level=fraud_level(score), reasons=known, checklist=checklist)
