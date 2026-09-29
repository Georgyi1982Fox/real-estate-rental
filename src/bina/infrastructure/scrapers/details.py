"""Разбор подробностей объявлений сайтов в наши коды (TASK-018)."""

import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

# Время на сайтах без часового пояса — тбилисское (UTC+4, без перехода на летнее)
TBILISI = timezone(timedelta(hours=4))

# Состояние по тексту сайта (страницы на русском); первое совпадение выигрывает
_CONDITION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("white_frame", re.compile(r"бел\w*\s+карк|white\s+frame|თეთრი", re.I)),
    ("black_frame", re.compile(r"черн\w*\s+карк|black\s+frame|შავი", re.I)),
    ("green_frame", re.compile(r"зел[её]н\w*\s+карк|green\s+frame|მწვანე", re.I)),
    (
        "under_renovation",
        re.compile(r"в\s+процессе|ид[её]т\s+ремонт|under\s+renovation|მიმდინარე", re.I),
    ),
    ("needs_renovation", re.compile(r"треб|нужда|без\s+ремонт|needs|საჭირო", re.I)),
    (
        "newly_renovated",
        re.compile(r"нов\w*\s+ремонт|недавно|newly|new\s+renov|ახალი\s+რემონტ", re.I),
    ),
    ("renovated", re.compile(r"ремонт|отремонт|renovat|რემონტ", re.I)),
)

AGENT_TYPES = {"agent", "broker", "agency", "company", "developer", "maklers"}
OWNER_TYPES = {"physical", "individual", "owner", "user", "person"}


def condition_code(text: Any) -> str | None:
    """Код состояния по тексту сайта («Новый ремонт» → ``newly_renovated``)."""
    if not isinstance(text, str) or not text.strip():
        return None
    for code, pattern in _CONDITION_PATTERNS:
        if pattern.search(text):
            return code
    return None


def owner_type_code(value: Any) -> str | None:
    """``owner`` / ``agent`` по типу пользователя сайта."""
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if lowered in AGENT_TYPES:
        return "agent"
    if lowered in OWNER_TYPES:
        return "owner"
    return None


def to_int(value: Any) -> int | None:
    """Целое из числа или строки («4», 4, «4+»); иначе None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        return int(match.group()) if match else None
    return None


def to_float(value: Any) -> float | None:
    """Число с плавающей точкой; 0 и мусор — None."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number or None


def to_datetime(value: Any) -> datetime | None:
    """Дата сайта: ISO с поясом или ``2026-09-27 12:08:19`` (время Тбилиси)."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    # Python до 3.11 не любит 7 знаков дробной части: обрезаем до микросекунд
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TBILISI)
    return parsed.astimezone(UTC)


def join_address(*parts: Any) -> str | None:
    """Адрес из частей без пустых («ул. Мачабели», «6» → «ул. Мачабели 6»)."""
    text = " ".join(str(part).strip() for part in parts if part not in (None, ""))
    text = re.sub(r"\s+", " ", text).strip(" ,")
    return text or None
