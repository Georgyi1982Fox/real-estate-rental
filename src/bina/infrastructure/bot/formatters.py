"""Форматирование объявлений для сообщений Telegram (HTML parse mode)."""

from decimal import Decimal
from html import escape

from src.bina.infrastructure.bot.texts import t
from src.bina.infrastructure.db.models import District, Listing

CURRENCY_SYMBOLS: dict[str, str] = {"GEL": "₾", "USD": "$", "EUR": "€"}
MAX_TITLE_LENGTH = 80


def format_number(value: Decimal | float | int) -> str:
    """Форматирует число с разделителем тысяч и без лишних нулей: ``1 250.5``."""
    number = Decimal(str(value))
    if number == number.to_integral_value():
        return f"{int(number):,}".replace(",", " ")
    return f"{number.normalize():,f}".replace(",", " ")


def format_price(price: Decimal | float | int, currency: str) -> str:
    """Форматирует цену с символом валюты: ``1 200 ₾``, ``$800``."""
    amount = format_number(price)
    symbol = CURRENCY_SYMBOLS.get(currency.upper())
    if symbol is None:
        return f"{amount} {currency.upper()}"
    if symbol == "$":
        return f"${amount}"
    return f"{amount} {symbol}"


def truncate(text: str, limit: int) -> str:
    """Обрезает текст до ``limit`` символов с многоточием."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def listing_title(listing: Listing, language: str) -> str:
    """Заголовок объявления на языке пользователя (с запасным вариантом)."""
    primary, fallback = (
        (listing.title_ka, listing.title_ru)
        if language == "ka"
        else (listing.title_ru, listing.title_ka)
    )
    return primary or fallback or "—"


def district_name(district: District, language: str) -> str:
    """Название района на языке пользователя."""
    names = {"ru": district.name_ru, "en": district.name_en, "ka": district.name_ka}
    return names.get(language) or district.name_ru or district.name_ka


def format_listing(listing: Listing, index: int, language: str) -> str:
    """Карточка объявления в списке.

    Пример::

        <b>1. Светлая квартира в Ваке</b>
        💰 1 200 ₾ · 🚪 2 комн. · 📐 55 м²
    """
    title = escape(truncate(listing_title(listing, language), MAX_TITLE_LENGTH))
    details = [
        f"💰 {format_price(listing.price, listing.currency)}",
        f"🚪 {t(language, 'listing_rooms', n=listing.rooms)}",
        f"📐 {t(language, 'listing_area', area=format_number(listing.area))}",
    ]
    if listing.is_verified:
        details.append("✅")
    return f"<b>{index}. {title}</b>\n" + " · ".join(details)


def format_listings(listings: list[Listing], start_index: int, language: str) -> str:
    """Список карточек, пронумерованных с ``start_index``."""
    return "\n\n".join(
        format_listing(listing, start_index + offset, language)
        for offset, listing in enumerate(listings)
    )
