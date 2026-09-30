"""Умный поиск по смыслу (TASK-012).

Каждое объявление превращается в вектор-«отпечаток смысла» (embedding): текст
объявления плюс его главные характеристики. Запрос пользователя («светлая
квартира с балконом рядом с метро») превращается в вектор той же моделью, и
выдача сортируется по близости векторов — совпадение слов не нужно, язык
запроса и объявления может быть разным.
"""

from bina.application.cities import city_name
from bina.application.rent_period import DAILY
from bina.infrastructure.db.models import Listing

# Размер вектора в bina_embeddings (Vector(1536))
EMBEDDING_DIM = 1536
# Сколько самых близких объявлений показывает умный поиск
SMART_LIMIT = 50
# Длинное описание обрезаем: суть объявления — в начале, а токены платные
MAX_DESCRIPTION = 1500
# Запрос короче — не поиск по смыслу (например, «ок», «да»)
MIN_QUERY_LETTERS = 3


def listing_text(listing: Listing) -> str:
    """Текст для embedding: характеристики + заголовок и описание (лучше по-английски)."""
    title = listing.title_en or listing.title_ru or listing.title_ka or ""
    description = listing.description_en or listing.description_ru or listing.description_ka or ""
    district = listing.district
    place = ", ".join(
        part
        for part in (
            district.name_en if district else "",
            city_name(district.city, "en") if district else "",
        )
        if part
    )
    daily = listing.rent_period == DAILY
    facts = [
        f"{listing.rooms}-room apartment for {'daily rent' if daily else 'rent'}",
        f"{float(listing.area):g} m²" if listing.area else "",
        f"{float(listing.price):g} {listing.currency} per {'day' if daily else 'month'}",
        place,
        f"floor {listing.floor}" if listing.floor is not None else "",
        (listing.condition or "").replace("_", " "),
        ", ".join(code.replace("_", " ") for code in listing.features or []),
    ]
    head = ". ".join(fact for fact in facts if fact)
    return f"{head}.\n{title}\n{description[:MAX_DESCRIPTION]}".strip()


def is_smart_query(text: str | None) -> bool:
    """Похоже ли на запрос: есть хотя бы несколько букв."""
    return sum(char.isalpha() for char in text or "") >= MIN_QUERY_LETTERS
