"""Заголовки объявлений на трёх языках из данных квартиры.

Заголовки сайтов («Аренда 2-комнатная Квартира. Мтацминда») написаны на одном
языке и ничего не добавляют к комнатам, району и площади, а перевод через AI
приходит не сразу. Поэтому заголовок любого объявления собирается сам, сразу на
ka/ru/en: «2-комн. квартира, Мтацминда, 35 м²». AI переводит только описание.
"""

from decimal import Decimal

from bina.application.rent_period import DAILY

LANGUAGES = ("ru", "en", "ka")
# Шаблон и приставка посуточной аренды (TASK-092)
_TEMPLATES = {
    "ru": ("{rooms}-комн. квартира, {district}, {area} м²", "Посуточно: "),
    "en": ("{rooms}-room apartment, {district}, {area} m²", "Daily: "),
    "ka": ("{rooms}-ოთახიანი ბინა, {district}, {area} მ²", "დღიურად: "),
}


def format_area(area: Decimal | float) -> str:
    """60 → «60», 45.50 → «45.5»."""
    return f"{Decimal(str(area)).normalize():f}"


def listing_titles(
    rooms: int, area: Decimal | float, rent_period: str | None, districts: dict[str, str]
) -> dict[str, str]:
    """``title_ru/en/ka``; ``districts`` — название района на языках (пустое — русское)."""
    fallback = districts.get("ru") or next((name for name in districts.values() if name), "")
    titles: dict[str, str] = {}
    for language, (template, daily) in _TEMPLATES.items():
        title = template.format(
            rooms=rooms, district=districts.get(language) or fallback, area=format_area(area)
        )
        titles[f"title_{language}"] = (daily if rent_period == DAILY else "") + title
    return titles
