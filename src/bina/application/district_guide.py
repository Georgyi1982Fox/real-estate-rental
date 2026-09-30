"""Справка по районам Тбилиси и Батуми (TASK-104, TASK-079) и центр района для карты (TASK-080).

Статичные данные: примерный центр района, есть ли метро, характер района и короткое
описание на ka / ru / en. Цены и число объявлений считаются по базе отдельно.
Время до центра — оценка по расстоянию до площади Свободы (в Батуми — площади
Европы), а не маршрут.
"""

import math
from dataclasses import dataclass
from enum import StrEnum

from bina.application.cities import BATUMI, TBILISI, city, in_city

Labels = dict[str, str]

# Площадь Свободы — «центр» Тбилиси (центры городов — в ``cities.CITIES``)
CITY_CENTER = city(TBILISI).center
# Средняя скорость по городу на машине, км/ч (с пробками)
CITY_SPEED_KMH = 20


class Tag(StrEnum):
    CENTRAL = "central"
    GREEN = "green"
    QUIET = "quiet"
    LIVELY = "lively"
    OLD_TOWN = "old_town"
    NEW_BUILDINGS = "new_buildings"
    AFFORDABLE = "affordable"
    PREMIUM = "premium"
    UNIVERSITIES = "universities"


TAG_LABELS: dict[Tag, Labels] = {
    Tag.CENTRAL: {"ka": "ცენტრთან ახლოს", "ru": "Близко к центру", "en": "Close to the centre"},
    Tag.GREEN: {"ka": "პარკები და მწვანე", "ru": "Парки и зелень", "en": "Parks and greenery"},
    Tag.QUIET: {"ka": "მშვიდი", "ru": "Тихий", "en": "Quiet"},
    Tag.LIVELY: {
        "ka": "კაფეები და ცხოვრება",
        "ru": "Кафе и оживлённые улицы",
        "en": "Cafés and lively streets",
    },
    Tag.OLD_TOWN: {"ka": "ისტორიული უბანი", "ru": "Исторический район", "en": "Historic area"},
    Tag.NEW_BUILDINGS: {"ka": "ახალი კორპუსები", "ru": "Новостройки", "en": "New buildings"},
    Tag.AFFORDABLE: {"ka": "ხელმისაწვდომი ფასები", "ru": "Доступные цены", "en": "Affordable"},
    Tag.PREMIUM: {"ka": "პრესტიჟული", "ru": "Престижный", "en": "Upscale"},
    Tag.UNIVERSITIES: {"ka": "უნივერსიტეტები", "ru": "Университеты", "en": "Universities"},
}


@dataclass(frozen=True, slots=True)
class DistrictGuide:
    latitude: float
    longitude: float
    metro: bool
    tags: tuple[Tag, ...] = ()
    about: Labels | None = None


def _about(ka: str, ru: str, en: str) -> Labels:
    return {"ka": ka, "ru": ru, "en": en}


T = Tag

# Ключ — английское название района (``District.name_en``)
GUIDE: dict[str, DistrictGuide] = {
    "Vake": DistrictGuide(
        41.7090,
        44.7580,
        False,
        (T.PREMIUM, T.GREEN, T.LIVELY),
        _about(
            "პრესტიჟული უბანი ვაკის პარკით, კაფეებითა და რესტორნებით ჭავჭავაძის გამზირზე.",
            "Престижный район с Ваке-парком, кафе и ресторанами на проспекте Чавчавадзе.",
            "Upscale area with Vake Park and cafés and restaurants along Chavchavadze Avenue.",
        ),
    ),
    "Saburtalo": DistrictGuide(
        41.7260,
        44.7560,
        True,
        (T.NEW_BUILDINGS, T.UNIVERSITIES, T.LIVELY),
        _about(
            "დიდი საცხოვრებელი უბანი მეტროთი, უნივერსიტეტებით, სავაჭრო ცენტრებითა "
            "და ბევრი ახალი კორპუსით.",
            "Большой жилой район с метро, университетами, торговыми центрами "
            "и множеством новостроек.",
            "Large residential area with the metro, universities, malls and many new buildings.",
        ),
    ),
    "Vake-Saburtalo": DistrictGuide(41.7180, 44.7550, True, (T.GREEN, T.NEW_BUILDINGS)),
    "Mtatsminda": DistrictGuide(
        41.6940,
        44.7960,
        True,
        (T.CENTRAL, T.OLD_TOWN, T.LIVELY),
        _about(
            "ქალაქის ცენტრი რუსთაველის გამზირით, თეატრებითა და მთაწმინდის პარკით.",
            "Центр города: проспект Руставели, театры и парк на горе Мтацминда.",
            "The city centre: Rustaveli Avenue, theatres and the park on Mtatsminda hill.",
        ),
    ),
    "Sololaki": DistrictGuide(
        41.6905,
        44.8010,
        True,
        (T.CENTRAL, T.OLD_TOWN),
        _about(
            "ძველი ქალაქის ლამაზი ქუჩები ისტორიული სახლებით, ყველაფერი ფეხით ახლოსაა.",
            "Красивые старые улицы с историческими домами, всё рядом пешком.",
            "Charming old streets with historic houses; everything is within walking distance.",
        ),
    ),
    "Old Tbilisi": DistrictGuide(
        41.6900,
        44.8070,
        True,
        (T.CENTRAL, T.OLD_TOWN, T.LIVELY),
        _about(
            "ისტორიული ცენტრი: აბანოები, ნარიყალა, ტურისტები და ბევრი რესტორანი.",
            "Исторический центр: серные бани, Нарикала, туристы и много ресторанов.",
            "Historic centre: sulphur baths, Narikala fortress, tourists and many restaurants.",
        ),
    ),
    "Vera": DistrictGuide(
        41.7050,
        44.7830,
        True,
        (T.CENTRAL, T.LIVELY, T.OLD_TOWN),
        _about(
            "მყუდრო ცენტრალური უბანი ძველი სახლებით, კაფეებითა და ვერის პარკით.",
            "Уютный центральный район со старыми домами, кафе и парком Вере.",
            "Cosy central area with old houses, cafés and Vere Park.",
        ),
    ),
    "Didube": DistrictGuide(
        41.7400,
        44.7820,
        True,
        (T.AFFORDABLE,),
        _about(
            "საცხოვრებელი უბანი მეტროთი და დიდი ავტოსადგურით, ფასები ცენტრზე დაბალია.",
            "Жилой район с метро и большим автовокзалом, цены ниже, чем в центре.",
            "Residential area with the metro and a big bus station; cheaper than the centre.",
        ),
    ),
    "Digomi": DistrictGuide(
        41.7650,
        44.7550,
        False,
        (T.NEW_BUILDINGS, T.QUIET),
        _about(
            "ახალი კორპუსები და კერძო სახლები, მშვიდი, მაგრამ ცენტრიდან შორს.",
            "Новостройки и частные дома, спокойно, но далеко от центра.",
            "New buildings and private houses; quiet but far from the centre.",
        ),
    ),
    "Digomi Massive": DistrictGuide(
        41.7560,
        44.7700,
        False,
        (T.AFFORDABLE, T.GREEN),
        _about(
            "საბჭოთა და ახალი კორპუსები, დიღმის ტყე-პარკი ახლოს.",
            "Советские и новые дома, рядом Дигомский лесопарк.",
            "Soviet-era and new blocks, next to the Digomi forest park.",
        ),
    ),
    "Chughureti": DistrictGuide(
        41.7170,
        44.8000,
        True,
        (T.CENTRAL, T.OLD_TOWN, T.AFFORDABLE),
        _about(
            "ცენტრთან ახლოს, აღმაშენებლის გამზირით და მარჯანიშვილით; ფასები ვაკეზე დაბალია.",
            "Рядом с центром: проспект Агмашенебели и Марджанишвили; дешевле, чем Ваке.",
            "Near the centre: Aghmashenebeli Avenue and Marjanishvili; cheaper than Vake.",
        ),
    ),
    "Didube-Chughureti": DistrictGuide(41.7300, 44.7900, True, (T.AFFORDABLE,)),
    "Nadzaladevi": DistrictGuide(
        41.7550,
        44.7900,
        True,
        (T.AFFORDABLE,),
        _about(
            "საცხოვრებელი უბანი მეტროთი, ძირითადად საბჭოთა კორპუსები, ხელმისაწვდომი ფასები.",
            "Спальный район с метро, в основном советские дома, доступные цены.",
            "Residential area with the metro, mostly Soviet-era blocks and affordable prices.",
        ),
    ),
    "Gldani": DistrictGuide(
        41.7950,
        44.8150,
        True,
        (T.AFFORDABLE,),
        _about(
            "ქალაქის ჩრდილოეთით დიდი საცხოვრებელი უბანი, მეტრო ახმეტელის სადგურამდე.",
            "Большой спальный район на севере города, метро до станции Ахметели.",
            "Large residential area in the north of the city, metro to Akhmeteli station.",
        ),
    ),
    "Gldani-Nadzaladevi": DistrictGuide(41.7750, 44.8050, True, (T.AFFORDABLE,)),
    "Isani": DistrictGuide(
        41.6950,
        44.8400,
        True,
        (T.AFFORDABLE,),
        _about(
            "მტკვრის მარცხენა ნაპირზე, მეტროთი ცენტრამდე რამდენიმე წუთი.",
            "Левый берег Куры, на метро до центра несколько минут.",
            "On the left bank of the Mtkvari river, a few minutes to the centre by metro.",
        ),
    ),
    "Samgori": DistrictGuide(
        41.6900,
        44.8700,
        True,
        (T.AFFORDABLE,),
        _about(
            "საცხოვრებელი უბანი მეტროთი, ერთ-ერთი ყველაზე ხელმისაწვდომი.",
            "Спальный район с метро, один из самых доступных по цене.",
            "Residential area with the metro, one of the most affordable.",
        ),
    ),
    "Isani-Samgori": DistrictGuide(41.6920, 44.8550, True, (T.AFFORDABLE,)),
    "Varketili": DistrictGuide(41.6970, 44.8900, True, (T.AFFORDABLE,)),
    "Avlabari": DistrictGuide(
        41.6930,
        44.8150,
        True,
        (T.CENTRAL, T.OLD_TOWN),
        _about(
            "ძველი უბანი სამების ტაძართან, მეტროთი და ცენტრთან ახლოს.",
            "Старый район у собора Самеба, с метро и рядом с центром.",
            "Old area by the Holy Trinity Cathedral, with the metro, close to the centre.",
        ),
    ),
    "Krtsanisi": DistrictGuide(41.6700, 44.8200, False, (T.QUIET, T.GREEN)),
    "Ortachala": DistrictGuide(41.6800, 44.8200, False, (T.NEW_BUILDINGS,)),
    "Vazisubani": DistrictGuide(41.7050, 44.8750, False, (T.AFFORDABLE,)),
    "Mukhiani": DistrictGuide(41.7700, 44.8350, False, (T.AFFORDABLE, T.QUIET)),
    "Vashlijvari": DistrictGuide(
        41.7280,
        44.7450,
        False,
        (T.QUIET, T.GREEN),
        _about(
            "მშვიდი უბანი საბურთალოს გვერდით, კერძო სახლები და ახალი კორპუსები.",
            "Тихий район рядом с Сабуртало: частные дома и новостройки.",
            "Quiet area next to Saburtalo with private houses and new buildings.",
        ),
    ),
    "Nutsubidze Plateau": DistrictGuide(41.7250, 44.7300, False, (T.GREEN, T.AFFORDABLE)),
    "Bagebi": DistrictGuide(41.7150, 44.7400, False, (T.QUIET, T.GREEN, T.NEW_BUILDINGS)),
    "Lisi": DistrictGuide(
        41.7400,
        44.7300,
        False,
        (T.QUIET, T.GREEN, T.NEW_BUILDINGS),
        _about(
            "ახალი კომპლექსები ლისის ტბასთან, სუფთა ჰაერი, მაგრამ მანქანა სასურველია.",
            "Новые комплексы у озера Лиси, чистый воздух, но лучше с машиной.",
            "New complexes by Lisi Lake with fresh air; a car is handy.",
        ),
    ),
    "Turtle Lake": DistrictGuide(41.7000, 44.7500, False, (T.GREEN, T.QUIET)),
    "Tbilisi": DistrictGuide(CITY_CENTER[0], CITY_CENTER[1], True),
}

_BATUMI_CENTER = city(BATUMI).center

# Батуми (TASK-079): метро нет
BATUMI_GUIDE: dict[str, DistrictGuide] = {
    "Old Batumi": DistrictGuide(
        41.6485,
        41.6380,
        False,
        (T.CENTRAL, T.OLD_TOWN, T.LIVELY),
        _about(
            "ისტორიული ცენტრი: პიაცა, ევროპის მოედანი, ბულვარი და ზღვა ფეხით.",
            "Исторический центр: Пьяцца, площадь Европы, бульвар и море пешком.",
            "Historic centre: Piazza, Europe Square, the boulevard and the sea on foot.",
        ),
    ),
    "New Boulevard": DistrictGuide(
        41.6250,
        41.6030,
        False,
        (T.NEW_BUILDINGS, T.PREMIUM),
        _about(
            "ახალი მაღალსართულიანი სახლები ზღვის სანაპიროზე.",
            "Новые высотки на берегу моря.",
            "New high-rises on the seafront.",
        ),
    ),
    "Makhinjauri": DistrictGuide(
        41.6740,
        41.6980,
        False,
        (T.GREEN, T.QUIET),
        _about(
            "მშვიდი დასახლება ქალაქის ჩრდილოეთით, ზღვასთან.",
            "Тихий посёлок к северу от города, у моря.",
            "A quiet settlement north of the city, by the sea.",
        ),
    ),
    "Gonio": DistrictGuide(
        41.5600,
        41.5720,
        False,
        (T.QUIET, T.AFFORDABLE),
        _about(
            "მშვიდი ადგილი ციხესიმაგრით და პლაჟით, ქალაქის სამხრეთით.",
            "Спокойное место с крепостью и пляжем к югу от города.",
            "A calm place with a fortress and a beach south of the city.",
        ),
    ),
    "Batumi": DistrictGuide(_BATUMI_CENTER[0], _BATUMI_CENTER[1], False),
}

GUIDES: dict[str, dict[str, DistrictGuide]] = {TBILISI: GUIDE, BATUMI: BATUMI_GUIDE}


def guide_for(name_en: str, city_code: str = TBILISI) -> DistrictGuide | None:
    """Справка по английскому названию района города; «Дигоми 3» → «Дигоми»."""
    guides = GUIDES.get(city_code, {})
    guide = guides.get(name_en)
    if guide is None:
        base = name_en.rstrip("0123456789 ").strip()
        guide = guides.get(base)
    return guide


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние по прямой (формула гаверсинусов)."""
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def minutes_to_center(latitude: float, longitude: float, city_code: str = TBILISI) -> int:
    """Примерно минут на машине до центра города (по прямой, плюс 30% на изгибы дорог)."""
    km = distance_km(latitude, longitude, *city(city_code).center) * 1.3
    return max(5, round(km / CITY_SPEED_KMH * 60 / 5) * 5)


# Прямоугольник вокруг Тбилиси: точки вне него считаем ошибкой геокодера
TBILISI_BOUNDS = city(TBILISI).bounds  # юг, запад, север, восток


def in_tbilisi(latitude: float, longitude: float) -> bool:
    return in_city(latitude, longitude, TBILISI)
