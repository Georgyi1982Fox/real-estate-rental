"""Объявления сайтов TNET: MyHome.ge и Livo.ge (TASK-092).

У обоих сайтов одна база объявлений (``api-statements.tnet.ge``) и один формат
объявления (``statement``): MyHome.ge кладёт его в страницу JSON-ом Next.js,
Livo.ge получает из API. Здесь — разбор ``statement`` в поля ``RawListing``.
"""

import re
from collections.abc import Iterator
from typing import Any

from bina.application.cities import city_name, city_of
from bina.application.listing_details import clean_features
from bina.application.rent_period import DAILY, MONTHLY
from bina.infrastructure.scrapers.details import (
    condition_code,
    owner_type_code,
    to_datetime,
    to_float,
    to_int,
)
from bina.infrastructure.scrapers.nextjs import walk

# Ключи цен в JSON сайта: price["1"] в лари, "2" в долларах, "3" в евро
CURRENCY_BY_ID = {"1": "GEL", "2": "USD", "3": "EUR"}
# deal_type_id: 2 — аренда помесячно, 7 — посуточно (statement-parameters API)
RENT_DEAL_TYPE = 2
DAILY_DEAL_TYPE = 7
# room_type_id → число комнат (id 1-5 совпадают с числом; дальше — «6+» и т. п.)
MAX_ROOM_TYPE = 5


def parse_rooms(text: str) -> int:
    """Количество комнат: ``2 комнаты``, ``3 room``, ``2 ოთახი``."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def clean_phone(text: str) -> str:
    """Телефон без лишних символов: ``+995 555 12-34-56`` → ``+995555123456``."""
    digits = re.sub(r"[^\d+]", "", text)
    return digits if len(re.sub(r"\D", "", digits)) >= 6 else ""


def statement_city(item: dict[str, Any], default: str) -> str:
    """Город объявления по ``city_id`` или ``city_name``; другой, не наш город — пустая строка."""
    if code := city_of(tnet_city_id=item.get("city_id")):
        return code
    name = str(item.get("city_name") or "").strip()
    if not name:
        return default
    return city_of(name) or ""


def is_statement(value: Any) -> bool:
    """Похоже ли значение на объявление сайта."""
    return (
        isinstance(value, dict)
        and "id" in value
        and "price" in value
        and ("dynamic_title" in value or "room" in value)
    )


def statement_lists(data: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
    """Списки объявлений в JSON страницы поиска."""
    for value in walk(data):
        if isinstance(value, list) and value and all(is_statement(item) for item in value):
            yield value


def find_statement(data: dict[str, Any]) -> dict[str, Any] | None:
    """Первое объявление в JSON страницы объявления."""
    for value in walk(data):
        if is_statement(value):
            return dict(value)
    return None


# Примерный курс к лари: только для проверки пересчёта сайта (точный курс — у сайта)
_ROUGH_GEL_RATE = {"1": 1.0, "2": 2.7, "3": 3.0}
# Пересчёт сайта в лари расходится с ценой хозяина больше чем на столько — он неверен
_GEL_MISMATCH = 0.25


def statement_price(item: dict[str, Any]) -> tuple[float, str]:
    """Цена в лари по пересчёту сайта, если он сходится с ценой хозяина.

    Пересчёт сайта бывает устаревшим: у объявления «750 $» в лари стояло 325 488 ₾ (старая
    цена продажи). Тогда берём цену в валюте, которую указал хозяин (в лари её переведёт
    нормализатор).
    """
    prices = item.get("price")
    if not isinstance(prices, dict):
        return 0.0, "GEL"
    currency_id = str(item.get("statement_currency_id") or item.get("currency_id") or "1")
    own = _price_total(prices, currency_id)
    gel = _price_total(prices, "1")
    if gel and own and currency_id in _ROUGH_GEL_RATE:
        expected = own * _ROUGH_GEL_RATE[currency_id]
        if abs(gel - expected) > expected * _GEL_MISMATCH:
            return own, CURRENCY_BY_ID.get(currency_id, "GEL")
    if gel:
        return gel, "GEL"
    if own:
        return own, CURRENCY_BY_ID.get(currency_id, "GEL")
    return 0.0, "GEL"


def _price_total(prices: dict[str, Any], key: str) -> float:
    entry = prices.get(key)
    if isinstance(entry, dict) and entry.get("price_total"):
        return float(entry["price_total"])
    return 0.0


def statement_photos(item: dict[str, Any]) -> list[str]:
    """Ссылки на фото в большом размере, главное первым."""
    images = item.get("images")
    if not isinstance(images, list):
        return []
    ordered = sorted(
        (image for image in images if isinstance(image, dict)),
        key=lambda image: not image.get("is_main"),
    )
    photos: list[str] = []
    for image in ordered:
        url = str(image.get("large") or image.get("thumb") or "")
        if url and url not in photos:
            photos.append(url)
    return photos


def statement_details(item: dict[str, Any]) -> dict[str, Any]:
    """Поля объявления со страницы объявления (только найденные)."""
    details: dict[str, Any] = {}
    if title := str(item.get("dynamic_title") or "").strip():
        details["title"] = title
    price, currency = statement_price(item)
    if price > 0:
        details["price"], details["currency"] = price, currency
    if district := str(item.get("urban_name") or item.get("district_name") or ""):
        details["district"] = district
    if rooms := statement_rooms(item):
        details["rooms"] = rooms
    if area := float(item.get("area") or 0):
        details["area"] = area
    description = item.get("description") or item.get("comment")
    if isinstance(description, str) and description.strip():
        details["description"] = description.strip()
    if photos := statement_photos(item):
        details["photos"] = photos
    # Сайт отдаёт номер замаскированным (``591589***``), полный только по кнопке: такие пропускаем
    for key in ("phone", "phone_number", "user_phone_number"):
        raw = item.get(key)
        if isinstance(raw, str | int) and "*" not in str(raw) and (phone := clean_phone(str(raw))):
            details["phone"] = phone
            break
    if owner := str(item.get("user_title") or item.get("owner_name") or "").strip():
        details["owner_name"] = owner
    details.update(statement_extras(item))
    details["has_details"] = True
    if item.get("is_active") is False:
        # Снято владельцем или истёк срок
        details["active"] = False
    return details


# Параметры (``parameters[].key``) страницы объявления → наши коды удобств
_TNET_FEATURES: dict[str, str] = {
    "furniture": "furniture",
    "kitchen": "kitchen_appliances",
    "conditioner": "air_conditioning",
    "air_conditioner": "air_conditioning",
    "heating": "heating",
    "hot_water": "hot_water",
    "washing_machine": "washing_machine",
    "dishwasher": "dishwasher",
    "refrigerator": "fridge",
    "tv": "tv",
    "internet": "internet",
    "wifi": "internet",
    "gas": "gas",
    "elevator": "elevator",
    "lift": "elevator",
    "parking": "parking",
    "garage": "parking",
    "balcony": "balcony",
    "loggia": "balcony",
    "storeroom": "storage",
    "pool": "pool",
    "swimming_pool": "pool",
    "pets": "pets_allowed",
    "pets_allowed": "pets_allowed",
    "alarm": "security",
    "security": "security",
}


def statement_extras(item: dict[str, Any]) -> dict[str, Any]:
    """Этажи, спальни, удобства, состояние, адрес, даты (из списка и страницы объявления)."""
    extras: dict[str, Any] = {}
    user_type = item.get("user_type")
    for key, value in (
        ("floor", to_int(item.get("floor"))),
        ("total_floors", to_int(item.get("total_floors"))),
        ("bedrooms", to_int(item.get("bedroom"))),
        ("condition", condition_code(item.get("condition"))),
        (
            "owner_type",
            owner_type_code(user_type.get("type") if isinstance(user_type, dict) else None),
        ),
        ("address", str(item.get("address") or "").strip() or None),
        ("latitude", to_float(item.get("lat"))),
        ("longitude", to_float(item.get("lng"))),
        ("published_at", to_datetime(item.get("created_at"))),
        ("updated_at", to_datetime(item.get("last_updated"))),
    ):
        if value is not None:
            extras[key] = value
    if (period := statement_rent_period(item)) is not None:
        extras["rent_period"] = period

    parameters = item.get("parameters")
    if isinstance(parameters, list) and parameters:
        codes = [
            _TNET_FEATURES[str(parameter.get("key"))]
            for parameter in parameters
            if isinstance(parameter, dict) and str(parameter.get("key")) in _TNET_FEATURES
        ]
        if to_int(item.get("balconies")):
            codes.append("balcony")
        for key, code in (
            ("heating_type_id", "heating"),
            ("hot_water_type_id", "hot_water"),
            ("parking_type_id", "parking"),
        ):
            if item.get(key):
                codes.append(code)
        extras["features"] = clean_features(codes)
    return extras


def statement_district(item: dict[str, Any], city: str) -> str:
    """Район; не указан (часто в Батуми) — город в целом, как у SS.ge."""
    name = str(item.get("urban_name") or item.get("district_name") or "").strip()
    return name or (city_name(city, "ru") if city else "Unknown")


def statement_rooms(item: dict[str, Any]) -> int:
    """Комнаты: ``room`` («3») в списке, ``room_type_id`` на странице объявления."""
    if rooms := parse_rooms(str(item.get("room") or "")):
        return rooms
    room_type = to_int(item.get("room_type_id"))
    return room_type if room_type is not None and 0 < room_type <= MAX_ROOM_TYPE else 0


def statement_rent_period(item: dict[str, Any]) -> str | None:
    """Вид аренды по ``deal_type_id``; не аренда или нет поля — ``None``."""
    deal_type = to_int(item.get("deal_type_id"))
    if deal_type == DAILY_DEAL_TYPE:
        return DAILY
    if deal_type == RENT_DEAL_TYPE:
        return MONTHLY
    return None
