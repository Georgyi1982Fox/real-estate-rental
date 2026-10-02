"""AI-анализ фото квартиры: состояние ремонта и видимые дефекты (TASK-114).

AI смотрит до ``MAX_PHOTOS`` фото объявления и отвечает: уровень ремонта
(``REPAIR_LEVELS``), какие проблемы видны (коды ``ISSUES``) и короткий вывод на трёх
языках. Уровень ремонта видят все (значок «🛠»), подробный разбор — Premium.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

# Фото с картинками в AI дорогие: для оценки ремонта хватает первых четырёх
MAX_PHOTOS = 4

EXCELLENT = "excellent"
GOOD = "good"
NEEDS_REPAIR = "needs_repair"
REPAIR_LEVELS: tuple[str, ...] = (EXCELLENT, GOOD, NEEDS_REPAIR)

ISSUES: tuple[str, ...] = (
    "mold",  # плесень
    "dampness",  # сырость, пятна от протечек
    "cracks",  # трещины в стенах или потолке
    "peeling",  # отслоившаяся краска или обои
    "old_appliances",  # старая техника
    "old_plumbing",  # старая сантехника
    "worn_furniture",  # изношенная мебель
    "worn_floor",  # изношенный пол
)

LEVEL_LABELS: dict[str, dict[str, str]] = {
    "ru": {EXCELLENT: "отличный ремонт", GOOD: "хороший ремонт", NEEDS_REPAIR: "нужен ремонт"},
    "en": {EXCELLENT: "excellent repair", GOOD: "good repair", NEEDS_REPAIR: "needs repair"},
    "ka": {
        EXCELLENT: "შესანიშნავი რემონტი",
        GOOD: "კარგი რემონტი",
        NEEDS_REPAIR: "სჭირდება რემონტი",
    },
}

ISSUE_LABELS: dict[str, dict[str, str]] = {
    "ru": {
        "mold": "Плесень",
        "dampness": "Сырость или следы протечек",
        "cracks": "Трещины на стенах или потолке",
        "peeling": "Отслоившаяся краска или обои",
        "old_appliances": "Старая техника",
        "old_plumbing": "Старая сантехника",
        "worn_furniture": "Изношенная мебель",
        "worn_floor": "Изношенный пол",
    },
    "en": {
        "mold": "Mold",
        "dampness": "Dampness or leak stains",
        "cracks": "Cracks in walls or ceiling",
        "peeling": "Peeling paint or wallpaper",
        "old_appliances": "Old appliances",
        "old_plumbing": "Old plumbing",
        "worn_furniture": "Worn furniture",
        "worn_floor": "Worn floor",
    },
    "ka": {
        "mold": "ობი (სოკო)",
        "dampness": "ნესტი ან ჟონვის კვალი",
        "cracks": "ბზარები კედელზე ან ჭერზე",
        "peeling": "აქერცლილი საღებავი ან შპალერი",
        "old_appliances": "ძველი ტექნიკა",
        "old_plumbing": "ძველი სანტექნიკა",
        "worn_furniture": "გაცვეთილი ავეჯი",
        "worn_floor": "გაცვეთილი იატაკი",
    },
}
SUMMARY_LANGUAGES: tuple[str, ...] = ("ru", "en", "ka")


@dataclass(frozen=True, slots=True)
class PhotoReport:
    """Вывод AI по фото."""

    level: str
    issues: tuple[str, ...] = ()
    # Язык → короткий вывод (2-3 предложения)
    summary: dict[str, str] = field(default_factory=dict)


def photos_for_analysis(images: Sequence[str] | None) -> list[str]:
    """Первые ``MAX_PHOTOS`` фото (обычно на первых — комнаты, кухня, санузел)."""
    return [url for url in (images or []) if url][:MAX_PHOTOS]


def photos_fingerprint(images: Sequence[str] | None) -> str:
    """Отпечаток набора фото: поменялись фото — анализ устарел."""
    joined = "\n".join(photos_for_analysis(images))
    return hashlib.sha1(joined.encode(), usedforsecurity=False).hexdigest()


def level_label(level: str | None, language: str) -> str:
    labels = LEVEL_LABELS.get(language, LEVEL_LABELS["ru"])
    return labels.get(level or "", "")


def issue_label(code: str, language: str) -> str:
    labels = ISSUE_LABELS.get(language, ISSUE_LABELS["ru"])
    return labels.get(code, "")
