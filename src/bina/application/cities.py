"""Города сервиса (TASK-079): Тбилиси, Батуми и другие города Грузии.

Код города (``tbilisi``) хранится у района (``District.city``); объявление
относится к городу своего района. Сайты пишут город по-разному
(«Тбилиси», «თბილისი», «Tbilisi», ss.ge — ещё и номером), ``city_of`` приводит
любое написание к коду.
"""

import re
from dataclasses import dataclass

Labels = dict[str, str]

TBILISI = "tbilisi"
BATUMI = "batumi"
KUTAISI = "kutaisi"
RUSTAVI = "rustavi"
ZUGDIDI = "zugdidi"
GORI = "gori"
POTI = "poti"
TELAVI = "telavi"
MTSKHETA = "mtskheta"
KOBULETI = "kobuleti"
BORJOMI = "borjomi"
BAKURIANI = "bakuriani"
GUDAURI = "gudauri"
TSKALTUBO = "tskaltubo"
KVARELI = "kvareli"
SIGHNAGHI = "sighnaghi"
STEPANTSMINDA = "stepantsminda"
AKHALTSIKHE = "akhaltsikhe"
OZURGETI = "ozurgeti"
ZESTAPONI = "zestaponi"
KHASHURI = "khashuri"
SENAKI = "senaki"
MARNEULI = "marneuli"
GONIO = "gonio"
UREKI = "ureki"
ANAKLIA = "anaklia"
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
    KUTAISI: City(
        code=KUTAISI,
        names={"ka": "ქუთაისი", "ru": "Кутаиси", "en": "Kutaisi"},
        center=(42.2597, 42.6634),
        bounds=(42.1671, 42.5681, 42.3524, 42.7719),
        aliases=("Kutaisor", "ქუთაისი"),
        tnet_city_id=96,
    ),
    RUSTAVI: City(
        code=RUSTAVI,
        names={"ka": "რუსთავი", "ru": "Рустави", "en": "Rustavi"},
        center=(41.5431, 45.0113),
        bounds=(41.4611, 44.8603, 41.6312, 45.1163),
        aliases=(),
        tnet_city_id=73,
    ),
    ZUGDIDI: City(
        code=ZUGDIDI,
        names={"ka": "ზუგდიდი", "ru": "Зугдиди", "en": "Zugdidi"},
        center=(42.5072, 41.8717),
        bounds=(42.4461, 41.7909, 42.5664, 41.9341),
        aliases=(),
    ),
    GORI: City(
        code=GORI,
        names={"ka": "გორი", "ru": "Гори", "en": "Gori"},
        center=(41.9818, 44.1118),
        bounds=(41.9339, 44.0528, 42.0467, 44.1934),
        aliases=(),
    ),
    POTI: City(
        code=POTI,
        names={"ka": "ფოთი", "ru": "Поти", "en": "Poti"},
        center=(42.1416, 41.6748),
        bounds=(42.0386, 41.5969, 42.239, 41.7499),
        aliases=("Фоты",),
        tnet_city_id=91,
    ),
    TELAVI: City(
        code=TELAVI,
        names={"ka": "თელავი", "ru": "Телави", "en": "Telavi"},
        center=(41.9197, 45.4703),
        bounds=(41.8727, 45.4109, 41.9771, 45.5655),
        aliases=(),
    ),
    MTSKHETA: City(
        code=MTSKHETA,
        names={"ka": "მცხეთა", "ru": "Мцхета", "en": "Mtskheta"},
        center=(41.8463, 44.7196),
        bounds=(41.7723, 44.6025, 41.9246, 44.7602),
        aliases=(),
    ),
    KOBULETI: City(
        code=KOBULETI,
        names={"ka": "ქობულეთი", "ru": "Кобулети", "en": "Kobuleti"},
        center=(41.8114, 41.7793),
        bounds=(41.7422, 41.7254, 41.942, 41.8657),
        aliases=(),
        tnet_city_id=94,
    ),
    BORJOMI: City(
        code=BORJOMI,
        names={"ka": "ბორჯომი", "ru": "Боржоми", "en": "Borjomi"},
        center=(41.8412, 43.3839),
        bounds=(41.7766, 43.3022, 41.9002, 43.475),
        aliases=(),
    ),
    BAKURIANI: City(
        code=BAKURIANI,
        names={"ka": "ბაკურიანი", "ru": "Бакуриани", "en": "Bakuriani"},
        center=(41.7511, 43.528),
        bounds=(41.6949, 43.4823, 41.7928, 43.5843),
        aliases=(),
    ),
    GUDAURI: City(
        code=GUDAURI,
        names={"ka": "გუდაური", "ru": "Гудаури", "en": "Gudauri"},
        center=(42.4766, 44.477),
        bounds=(42.4266, 44.427, 42.5266, 44.527),
        aliases=(),
    ),
    TSKALTUBO: City(
        code=TSKALTUBO,
        names={"ka": "წყალტუბო", "ru": "Цхалтубо", "en": "Tskaltubo"},
        center=(42.3233, 42.6016),
        bounds=(42.2596, 42.5507, 42.367, 42.6503),
        aliases=("Цкалтубо",),
    ),
    KVARELI: City(
        code=KVARELI,
        names={"ka": "ყვარელი", "ru": "Кварели", "en": "Kvareli"},
        center=(41.9482, 45.814),
        bounds=(41.8985, 45.7613, 42.007, 45.8656),
        aliases=(),
    ),
    SIGHNAGHI: City(
        code=SIGHNAGHI,
        names={"ka": "სიღნაღი", "ru": "Сигнахи", "en": "Sighnaghi"},
        center=(41.619, 45.9228),
        bounds=(41.5671, 45.8813, 41.6557, 45.9714),
        aliases=("Signagi", "Сигнаги"),
    ),
    STEPANTSMINDA: City(
        code=STEPANTSMINDA,
        names={"ka": "სტეფანწმინდა", "ru": "Степанцминда", "en": "Stepantsminda"},
        center=(42.658, 44.6408),
        bounds=(42.6174, 44.5979, 42.6964, 44.6822),
        aliases=("Kazbegi", "Казбеги", "ყაზბეგი"),
    ),
    AKHALTSIKHE: City(
        code=AKHALTSIKHE,
        names={"ka": "ახალციხე", "ru": "Ахалцихе", "en": "Akhaltsikhe"},
        center=(41.6396, 42.9859),
        bounds=(41.5789, 42.928, 41.6924, 43.0717),
        aliases=(),
    ),
    OZURGETI: City(
        code=OZURGETI,
        names={"ka": "ოზურგეთი", "ru": "Озургети", "en": "Ozurgeti"},
        center=(41.9231, 42.0059),
        bounds=(41.8668, 41.8702, 41.9729, 42.0648),
        aliases=(),
    ),
    ZESTAPONI: City(
        code=ZESTAPONI,
        names={"ka": "ზესტაფონი", "ru": "Зестафони", "en": "Zestaponi"},
        center=(42.1074, 43.0393),
        bounds=(42.0601, 42.9756, 42.1573, 43.1006),
        aliases=(),
    ),
    KHASHURI: City(
        code=KHASHURI,
        names={"ka": "ხაშური", "ru": "Хашури", "en": "Khashuri"},
        center=(41.9973, 43.5989),
        bounds=(41.9469, 43.5394, 42.0413, 43.6515),
        aliases=(),
    ),
    SENAKI: City(
        code=SENAKI,
        names={"ka": "სენაკი", "ru": "Сенаки", "en": "Senaki"},
        center=(42.2697, 42.0635),
        bounds=(42.2291, 42.0077, 42.3132, 42.1277),
        aliases=(),
    ),
    MARNEULI: City(
        code=MARNEULI,
        names={"ka": "მარნეული", "ru": "Марнеули", "en": "Marneuli"},
        center=(41.4718, 44.816),
        bounds=(41.4234, 44.7554, 41.5406, 44.869),
        aliases=(),
    ),
    GONIO: City(
        code=GONIO,
        names={"ka": "გონიო", "ru": "Гонио", "en": "Gonio"},
        center=(41.5674, 41.5707),
        bounds=(41.5215, 41.5336, 41.6125, 41.6121),
        aliases=(),
    ),
    UREKI: City(
        code=UREKI,
        names={"ka": "ურეკი", "ru": "Уреки", "en": "Ureki"},
        center=(41.9969, 41.7793),
        bounds=(41.9391, 41.7251, 42.054, 41.8373),
        aliases=(),
    ),
    ANAKLIA: City(
        code=ANAKLIA,
        names={"ka": "ანაკლია", "ru": "Анаклия", "en": "Anaklia"},
        center=(42.3954, 41.5657),
        bounds=(42.3326, 41.527, 42.4459, 41.6697),
        aliases=(),
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
    """``"tbilisi,batumi"`` → коды городов; ``"all"`` или пусто — все города Грузии.

    Неизвестный код — ошибка настройки (чтобы опечатку заметили сразу).
    """
    codes = tuple(part.strip().lower() for part in raw.split(",") if part.strip())
    if not codes or codes == ("all",):
        return tuple(CITIES)
    unknown = [code for code in codes if code not in CITIES]
    if unknown:
        raise ValueError(f"unknown cities: {', '.join(unknown)} (known: {', '.join(CITIES)})")
    return codes


def _locative_ka(name: str) -> str:
    """«ბათუმი» → «ბათუმში» (в Батуми)."""
    return (name[:-1] if name.endswith("ი") else name) + "ში"


# «квартира в Батуми», «ბინა ბათუმში», «flat in Batumi»: где квартира по словам объявления
_CITY_MENTIONS: dict[str, re.Pattern[str]] = {
    code: re.compile(
        "|".join(
            [
                rf"(?<![\w-])в\s+{re.escape(info.names['ru'])}(?![\w-])",
                rf"(?<![\w-])in\s+{re.escape(info.names['en'])}(?![\w-])",
                re.escape(_locative_ka(info.names["ka"])),
            ]
        ),
        re.IGNORECASE,
    )
    for code, info in CITIES.items()
}


def city_in_text(text: str) -> str | None:
    """Город, в котором квартира по словам объявления («сдаётся квартира в Батуми»).

    Назван ровно один город — его код, иначе (ни одного или несколько) — ``None``.
    """
    found = {code for code, pattern in _CITY_MENTIONS.items() if pattern.search(text or "")}
    return found.pop() if len(found) == 1 else None
