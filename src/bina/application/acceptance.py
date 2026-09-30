"""Акт приёмки квартиры: чек-лист и данные для PDF (TASK-102).

При въезде арендатор с хозяином проходят по списку (стены, сантехника, электрика,
техника, мебель…) и отмечают состояние каждого пункта. Акт с подписями защищает
залог: дефекты, записанные при въезде, не удержат из депозита при выезде.
Все названия — на ka / ru / en.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

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


_CITY: Labels = {"ka": "თბილისი", "ru": "Тбилиси", "en": "Tbilisi"}


def _intro(data: AcceptanceData, lang: str) -> list[str]:
    day = f"{data.handover_date:%d.%m.%Y}"
    city = _CITY[lang] if data.city == "Tbilisi" else data.city
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

    Порядок — как в чек-листе, а не как пришли пункты.
    """
    by_code = {item.code: item for item in data.items}
    rows = []
    for section in CHECKLIST:
        for checklist_item in section.items:
            checked = by_code.get(checklist_item.code)
            if checked is None:
                continue
            labels = checklist_item.labels
            status = STATUS_LABELS[checked.status]
            rows.append(
                (
                    f"{labels['ka']} / {labels[second_language]}",
                    f"{status['ka']} / {status[second_language]}",
                    checked.comment,
                )
            )
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
