"""Акт приёмки квартиры: чек-лист и данные для PDF (TASK-102).

При въезде арендатор с хозяином проходят по списку (стены, сантехника, электрика,
техника, мебель…) и отмечают состояние каждого пункта. Акт с подписями защищает
залог: дефекты, записанные при въезде, не удержат из депозита при выезде.
Все названия — на ka / ru / en.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from bina.application.cities import city_name, city_of

Labels = dict[str, str]


class ItemStatus(StrEnum):
    """Состояние пункта."""

    OK = "ok"
    DEFECT = "defect"
    MISSING = "missing"


STATUS_LABELS: dict[ItemStatus, Labels] = {
    ItemStatus.OK: {"ka": "წესრიგშია", "ru": "В порядке", "en": "OK"},
    ItemStatus.DEFECT: {"ka": "დეფექტი", "ru": "Дефект", "en": "Defect"},
    ItemStatus.MISSING: {"ka": "არ არის", "ru": "Отсутствует", "en": "Missing"},
}


@dataclass(frozen=True, slots=True)
class ChecklistItem:
    code: str
    labels: Labels


@dataclass(frozen=True, slots=True)
class ChecklistSection:
    code: str
    labels: Labels
    items: tuple[ChecklistItem, ...]


def _item(code: str, ka: str, ru: str, en: str) -> ChecklistItem:
    return ChecklistItem(code, {"ka": ka, "ru": ru, "en": en})


CHECKLIST: tuple[ChecklistSection, ...] = (
    ChecklistSection(
        "rooms",
        {"ka": "ოთახები", "ru": "Комнаты", "en": "Rooms"},
        (
            _item(
                "entrance_door",
                "შესასვლელი კარი და საკეტები",
                "Входная дверь и замки",
                "Entrance door and locks",
            ),
            _item("interior_doors", "შიდა კარები", "Межкомнатные двери", "Interior doors"),
            _item("windows", "ფანჯრები და რაფები", "Окна и подоконники", "Windows and sills"),
            _item("walls", "კედლები და ჭერი", "Стены и потолок", "Walls and ceiling"),
            _item("floors", "იატაკი", "Полы", "Floors"),
            _item("balcony", "აივანი", "Балкон", "Balcony"),
        ),
    ),
    ChecklistSection(
        "kitchen",
        {"ka": "სამზარეულო", "ru": "Кухня", "en": "Kitchen"},
        (
            _item("stove", "ქურა და ღუმელი", "Плита и духовка", "Stove and oven"),
            _item("fridge", "მაცივარი", "Холодильник", "Fridge"),
            _item("kitchen_sink", "ნიჟარა და ონკანი", "Мойка и смеситель", "Sink and faucet"),
            _item("kitchen_furniture", "სამზარეულოს ავეჯი", "Кухонная мебель", "Kitchen furniture"),
            _item("hood", "გამწოვი", "Вытяжка", "Cooker hood"),
        ),
    ),
    ChecklistSection(
        "bathroom",
        {"ka": "სააბაზანო", "ru": "Ванная", "en": "Bathroom"},
        (
            _item("toilet", "უნიტაზი", "Унитаз", "Toilet"),
            _item("shower", "შხაპი / აბაზანა", "Душ / ванна", "Shower / bath"),
            _item("bathroom_sink", "ხელსაბანი", "Раковина", "Washbasin"),
            _item(
                "water_heater",
                "წყლის გამაცხელებელი / ქვაბი",
                "Водонагреватель / котёл",
                "Water heater / boiler",
            ),
            _item(
                "leaks_mold", "ჟონვა და ობი არ არის", "Нет протечек и плесени", "No leaks or mould"
            ),
        ),
    ),
    ChecklistSection(
        "engineering",
        {
            "ka": "ელექტროობა და გათბობა",
            "ru": "Электрика и отопление",
            "en": "Electrics and heating",
        },
        (
            _item(
                "sockets",
                "როზეტები და ჩამრთველები",
                "Розетки и выключатели",
                "Sockets and switches",
            ),
            _item("lighting", "განათება", "Освещение", "Lighting"),
            _item(
                "heating", "გათბობა / რადიატორები", "Отопление / радиаторы", "Heating / radiators"
            ),
            _item("air_conditioner", "კონდიციონერი", "Кондиционер", "Air conditioner"),
            _item("internet", "ინტერნეტი / როუტერი", "Интернет / роутер", "Internet / router"),
        ),
    ),
    ChecklistSection(
        "furniture",
        {"ka": "ავეჯი და ტექნიკა", "ru": "Мебель и техника", "en": "Furniture and appliances"},
        (
            _item("washing_machine", "სარეცხი მანქანა", "Стиральная машина", "Washing machine"),
            _item("tv", "ტელევიზორი", "Телевизор", "TV"),
            _item("bed", "საწოლი და ლეიბი", "Кровать и матрас", "Bed and mattress"),
            _item("sofa", "დივანი", "Диван", "Sofa"),
            _item("wardrobe", "კარადა", "Шкаф", "Wardrobe"),
            _item("table_chairs", "მაგიდა და სკამები", "Стол и стулья", "Table and chairs"),
        ),
    ),
)

ITEMS: dict[str, ChecklistItem] = {
    item.code: item for section in CHECKLIST for item in section.items
}

# --- Комнаты (дизайн 2026-10): человек сам добавляет комнаты, которые есть в квартире
# (несколько спален, две ванные…), и у каждой — свой список пунктов. Код пункта комнаты:
# ``<тип>-<номер>:<пункт>``, например ``bedroom-2:windows``. Старые коды разделов
# (``entrance_door``…) по-прежнему принимаются — черновики, начатые до этого.


@dataclass(frozen=True, slots=True)
class RoomType:
    code: str
    labels: Labels
    items: tuple[ChecklistItem, ...]
    # Сколько таких комнат можно добавить
    max_count: int


_DOOR = _item("door", "კარი", "Дверь", "Door")
_WINDOWS = ITEMS["windows"]
_WALLS = ITEMS["walls"]
_FLOORS = ITEMS["floors"]
_SOCKETS = ITEMS["sockets"]
_LIGHTING = ITEMS["lighting"]
_HEATING = ITEMS["heating"]
_AIR_CONDITIONER = ITEMS["air_conditioner"]

ROOMS: tuple[RoomType, ...] = (
    RoomType(
        "hallway",
        {"ka": "დერეფანი", "ru": "Прихожая", "en": "Hallway"},
        (
            ITEMS["entrance_door"],
            _WALLS,
            _FLOORS,
            _LIGHTING,
            _item("hall_wardrobe", "კარადა / საკიდი", "Шкаф / вешалка", "Wardrobe / coat rack"),
            _item("intercom", "დომოფონი", "Домофон", "Intercom"),
        ),
        max_count=2,
    ),
    RoomType(
        "living_room",
        {"ka": "მისაღები ოთახი", "ru": "Гостиная", "en": "Living room"},
        (
            _DOOR,
            _WINDOWS,
            _WALLS,
            _FLOORS,
            _SOCKETS,
            _LIGHTING,
            _HEATING,
            _AIR_CONDITIONER,
            ITEMS["sofa"],
            ITEMS["table_chairs"],
            ITEMS["tv"],
        ),
        max_count=2,
    ),
    RoomType(
        "bedroom",
        {"ka": "საძინებელი", "ru": "Спальня", "en": "Bedroom"},
        (
            _DOOR,
            _WINDOWS,
            _WALLS,
            _FLOORS,
            _SOCKETS,
            _LIGHTING,
            _HEATING,
            _AIR_CONDITIONER,
            ITEMS["bed"],
            ITEMS["wardrobe"],
        ),
        max_count=6,
    ),
    RoomType(
        "kitchen",
        {"ka": "სამზარეულო", "ru": "Кухня", "en": "Kitchen"},
        (
            _WINDOWS,
            _WALLS,
            _FLOORS,
            _SOCKETS,
            _LIGHTING,
            ITEMS["stove"],
            ITEMS["fridge"],
            ITEMS["kitchen_sink"],
            ITEMS["kitchen_furniture"],
            ITEMS["hood"],
            _item("dishwasher", "ჭურჭლის სარეცხი მანქანა", "Посудомоечная машина", "Dishwasher"),
        ),
        max_count=2,
    ),
    RoomType(
        "bathroom",
        {"ka": "სააბაზანო", "ru": "Ванная и туалет", "en": "Bathroom"},
        (
            _DOOR,
            _item("tiles", "კედლები და ფილები", "Стены и плитка", "Walls and tiles"),
            _FLOORS,
            _LIGHTING,
            ITEMS["toilet"],
            ITEMS["shower"],
            ITEMS["bathroom_sink"],
            ITEMS["water_heater"],
            ITEMS["washing_machine"],
            ITEMS["leaks_mold"],
        ),
        max_count=4,
    ),
    RoomType(
        "balcony",
        {"ka": "აივანი", "ru": "Балкон", "en": "Balcony"},
        (
            _item("balcony_door", "აივნის კარი", "Дверь на балкон", "Balcony door"),
            _item("glazing", "შემინვა", "Остекление", "Glazing"),
            _item("railing", "მოაჯირი", "Перила", "Railing"),
            _FLOORS,
        ),
        max_count=3,
    ),
    RoomType(
        "whole",
        {"ka": "მთელი ბინა", "ru": "Вся квартира", "en": "Whole apartment"},
        (
            _item("cleanliness", "სისუფთავე", "Чистота", "Cleanliness"),
            _item("heating_boiler", "გათბობის ქვაბი", "Котёл отопления", "Heating boiler"),
            ITEMS["internet"],
        ),
        max_count=1,
    ),
)

ROOM_TYPES: dict[str, RoomType] = {room.code: room for room in ROOMS}
# Пунктов в акте не больше, чем во всех комнатах, добавленных до предела, плюс старые коды
MAX_ITEMS = len(ITEMS) + sum(len(room.items) * room.max_count for room in ROOMS)


@dataclass(frozen=True, slots=True)
class RoomItem:
    room: RoomType
    number: int
    item: ChecklistItem


def room_item(code: str) -> RoomItem | None:
    """``bedroom-2:windows`` → спальня №2, «Окна»; другое или неверный номер — ``None``."""
    place, separator, item_code = code.partition(":")
    room_code, dash, number = place.rpartition("-")
    room = ROOM_TYPES.get(room_code)
    if not separator or not dash or room is None or not number.isdigit():
        return None
    index = int(number)
    if not 1 <= index <= room.max_count:
        return None
    item = next((candidate for candidate in room.items if candidate.code == item_code), None)
    return RoomItem(room, index, item) if item is not None else None


def is_known_item(code: str) -> bool:
    """Пункт старого чек-листа или пункт добавленной комнаты."""
    return code in ITEMS or room_item(code) is not None


TITLES: Labels = {
    "ka": "ბინის მიღება-ჩაბარების აქტი",
    "ru": "Акт приёма-передачи квартиры",
    "en": "Apartment Handover Report",
}

DISCLAIMER: Labels = {
    "ka": "ეს არის აქტის ნიმუში. რეკომენდებულია ბინის ფოტოების გადაღება მიღების დღეს და "
    "მათი შენახვა აქტთან ერთად.",
    "ru": "Это образец акта. Рекомендуем в день приёмки сфотографировать квартиру и "
    "сохранить фото вместе с актом.",
    "en": "This is a sample report. We recommend taking photos of the apartment on the "
    "handover day and keeping them with this report.",
}


@dataclass(frozen=True, slots=True)
class CheckedItem:
    code: str
    status: ItemStatus
    comment: str = ""


@dataclass(frozen=True, slots=True)
class AcceptanceData:
    """Данные акта."""

    landlord_name: str
    tenant_name: str
    address: str
    handover_date: date
    items: tuple[CheckedItem, ...]
    keys: int | None = None
    electricity: str = ""
    gas: str = ""
    water: str = ""
    notes: str = ""
    city: str = "Tbilisi"


def _intro(data: AcceptanceData, lang: str) -> list[str]:
    day = f"{data.handover_date:%d.%m.%Y}"
    code = city_of(data.city)
    city = city_name(code, lang) if code else data.city
    if lang == "ka":
        return [
            f"გამქირავებელი: {data.landlord_name}. დამქირავებელი: {data.tenant_name}.",
            f"მისამართი: ქ. {city}, {data.address}. თარიღი: {day}.",
            "გამქირავებელმა გადასცა, ხოლო დამქირავებელმა მიიღო ბინა ქვემოთ აღწერილ მდგომარეობაში.",
        ]
    if lang == "ru":
        return [
            f"Арендодатель: {data.landlord_name}. Арендатор: {data.tenant_name}.",
            f"Адрес: г. {city}, {data.address}. Дата: {day}.",
            "Арендодатель передал, а Арендатор принял квартиру в состоянии, описанном ниже.",
        ]
    return [
        f"Landlord: {data.landlord_name}. Tenant: {data.tenant_name}.",
        f"Address: {data.address}, {city}. Date: {day}.",
        "The Landlord handed over and the Tenant accepted the apartment in the condition "
        "described below.",
    ]


def intro_rows(data: AcceptanceData, second_language: str) -> list[tuple[str, str]]:
    """Вступление: пары (грузинский, второй язык)."""
    return list(zip(_intro(data, "ka"), _intro(data, second_language), strict=True))


def item_rows(data: AcceptanceData, second_language: str) -> list[tuple[str, str, str]]:
    """Строки таблицы: (пункт ka / 2-й язык, состояние ka / 2-й язык, комментарий).

    Порядок — как в чек-листе, а не как пришли пункты: сначала старые разделы, потом
    комнаты в порядке типов и номеров. Пункт комнаты подписан комнатой: «Спальня 2 — Окна»;
    номер — только если таких комнат в акте несколько (или это не первая).
    """
    by_code = {item.code: item for item in data.items}
    rows = []

    def add(label: Labels, checked: CheckedItem) -> None:
        status = STATUS_LABELS[checked.status]
        rows.append(
            (
                f"{label['ka']} / {label[second_language]}",
                f"{status['ka']} / {status[second_language]}",
                checked.comment,
            )
        )

    for section in CHECKLIST:
        for checklist_item in section.items:
            checked = by_code.get(checklist_item.code)
            if checked is not None:
                add(checklist_item.labels, checked)

    found = [(found, by_code[code]) for code in by_code if (found := room_item(code)) is not None]
    numbers: dict[str, set[int]] = {}
    for place, _ in found:
        numbers.setdefault(place.room.code, set()).add(place.number)
    order = {room.code: index for index, room in enumerate(ROOMS)}

    def position(entry: tuple[RoomItem, CheckedItem]) -> tuple[int, int, int]:
        place = entry[0]
        return order[place.room.code], place.number, place.room.items.index(place.item)

    for place, checked in sorted(found, key=position):
        numbered = place.number > 1 or len(numbers[place.room.code]) > 1
        label = {
            language: (
                f"{place.room.labels[language]}{f' {place.number}' if numbered else ''} — "
                f"{place.item.labels[language]}"
            )
            for language in ("ka", "ru", "en")
        }
        add(label, checked)
    return rows


_METERS: dict[str, Labels] = {
    "electricity": {
        "ka": "ელექტროენერგიის მრიცხველი",
        "ru": "Счётчик электричества",
        "en": "Electricity meter",
    },
    "gas": {"ka": "გაზის მრიცხველი", "ru": "Счётчик газа", "en": "Gas meter"},
    "water": {"ka": "წყლის მრიცხველი", "ru": "Счётчик воды", "en": "Water meter"},
    "keys": {"ka": "გადაცემული გასაღებები", "ru": "Передано ключей", "en": "Keys handed over"},
    "notes": {"ka": "შენიშვნები", "ru": "Примечания", "en": "Notes"},
}


def meter_rows(data: AcceptanceData, second_language: str) -> list[tuple[str, str]]:
    """Показания счётчиков, ключи и примечания: (подпись ka / 2-й язык, значение)."""
    values = {
        "electricity": data.electricity,
        "gas": data.gas,
        "water": data.water,
        "keys": "" if data.keys is None else str(data.keys),
        "notes": data.notes,
    }
    return [
        (f"{_METERS[key]['ka']} / {_METERS[key][second_language]}", value)
        for key, value in values.items()
        if value
    ]


HEADERS: dict[str, Labels] = {
    "item": {"ka": "პუნქტი", "ru": "Пункт", "en": "Item"},
    "status": {"ka": "მდგომარეობა", "ru": "Состояние", "en": "Condition"},
    "comment": {"ka": "კომენტარი", "ru": "Комментарий", "en": "Comment"},
}


def header_row(second_language: str) -> tuple[str, str, str]:
    item, status, comment = (
        f"{HEADERS[key]['ka']} / {HEADERS[key][second_language]}"
        for key in ("item", "status", "comment")
    )
    return item, status, comment
