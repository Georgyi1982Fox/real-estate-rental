"""Города сервиса (TASK-079): Тбилиси и Батуми.

Код города (``tbilisi``) хранится у района (``District.city``); объявление
относится к городу своего района. Сайты пишут город по-разному
(«Тбилиси», «თბილისი», «Tbilisi», ss.ge — ещё и номером), ``city_of`` приводит
любое написание к коду.
"""

from dataclasses import dataclass

Labels = dict[str, str]

TBILISI = "tbilisi"
BATUMI = "batumi"
DEFAULT_CITY = TBILISI


@dataclass(frozen=True, slots=True)
class City:
    code: str
    names: Labels
    # «Центр города» для времени в пути: площадь Свободы / площадь Европы
    center: tuple[float, float]
    # Прямоугольник вокруг города (юг, запад, север, восток): точка вне — ошибка геокодера
    bounds: tuple[float, float, float, float]
    aliases: tuple[str, ...] = ()
    # address.cityId на ss.ge
    ss_city_id: int | None = None
    # city_id на сайтах TNET: myhome.ge, livo.ge (TASK-092)
    tnet_city_id: int | None = None


CITIES: dict[str, City] = {
    TBILISI: City(
        code=TBILISI,
        names={"ka": "თბილისი", "ru": "Тбилиси", "en": "Tbilisi"},
        center=(41.6938, 44.8015),
        bounds=(41.60, 44.60, 41.87, 45.05),
        aliases=("Tiflis", "Тифлис"),
        ss_city_id=95,
        tnet_city_id=1,
    ),
    BATUMI: City(
        code=BATUMI,
        names={"ka": "ბათუმი", "ru": "Батуми", "en": "Batumi"},
        center=(41.6509, 41.6363),
        bounds=(41.54, 41.55, 41.72, 41.80),
        aliases=("Батум",),
        ss_city_id=96,
        tnet_city_id=15,
    ),
}

_BY_NAME: dict[str, str] = {
    alias.lower(): city.code
    for city in CITIES.values()
    for alias in (city.code, *city.names.values(), *city.aliases)
}
_BY_SS_ID: dict[int, str] = {
    city.ss_city_id: city.code for city in CITIES.values() if city.ss_city_id is not None
}
_BY_TNET_ID: dict[int, str] = {
    city.tnet_city_id: city.code for city in CITIES.values() if city.tnet_city_id is not None
}


def city_of(
    name: str | None = None, *, ss_city_id: object = None, tnet_city_id: object = None
) -> str | None:
    """Код города по названию на любом языке или по номеру ss.ge / TNET; ``None`` — не наш."""
    if isinstance(ss_city_id, int) and ss_city_id in _BY_SS_ID:
        return _BY_SS_ID[ss_city_id]
    if isinstance(tnet_city_id, int) and tnet_city_id in _BY_TNET_ID:
        return _BY_TNET_ID[tnet_city_id]
    if not name:
        return None
    return _BY_NAME.get(name.strip().lower())


def city(code: str | None) -> City:
    """Город по коду; неизвестный код — Тбилиси."""
    return CITIES.get(code or DEFAULT_CITY, CITIES[DEFAULT_CITY])


def city_name(code: str | None, language: str) -> str:
    names = city(code).names
    return names.get(language, names["en"])


def in_city(latitude: float, longitude: float, code: str | None) -> bool:
    south, west, north, east = city(code).bounds
    return south <= latitude <= north and west <= longitude <= east


def parse_cities(raw: str) -> tuple[str, ...]:
    """``"tbilisi,batumi"`` → коды городов; неизвестные — ошибка настройки."""
    codes = tuple(part.strip().lower() for part in raw.split(",") if part.strip())
    unknown = [code for code in codes if code not in CITIES]
    if unknown:
        raise ValueError(f"unknown cities: {', '.join(unknown)} (known: {', '.join(CITIES)})")
    return codes or (DEFAULT_CITY,)
