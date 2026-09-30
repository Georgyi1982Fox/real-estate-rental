"""Двуязычный договор аренды квартиры (TASK-101).

Пункты договора на грузинском и на втором языке (русском или английском) —
в PDF они идут параллельно, в две колонки. Это образец для сторон, а не
юридическая консультация: дисклеймер — в конце документа.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from bina.application.cities import city_name, city_of


class Utilities(StrEnum):
    """Кто платит коммунальные."""

    TENANT = "tenant"
    LANDLORD = "landlord"
    INCLUDED = "included"


@dataclass(frozen=True, slots=True)
class ContractData:
    """Данные договора: из объявления и из анкеты пользователя."""

    landlord_name: str
    tenant_name: str
    address: str
    rooms: int
    area: float
    start: date
    months: int
    rent: Decimal
    currency: str
    deposit: Decimal
    payment_day: int
    utilities: Utilities
    pets_allowed: bool
    city: str = "Tbilisi"
    landlord_id: str = ""
    tenant_id: str = ""
    notes: str = ""


# Второй язык договора (первый — всегда грузинский)
SECOND_LANGUAGES = ("ru", "en")

_CURRENCY = {
    "GEL": {"ka": "ლარი", "ru": "лари", "en": "GEL"},
    "USD": {"ka": "აშშ დოლარი", "ru": "долларов США", "en": "USD"},
    "EUR": {"ka": "ევრო", "ru": "евро", "en": "EUR"},
}

TITLES = {
    "ka": "ბინის ქირავნობის ხელშეკრულება",
    "ru": "Договор аренды квартиры",
    "en": "Apartment Lease Agreement",
}

DISCLAIMER = {
    "ka": "ეს არის ხელშეკრულების ნიმუში. ხელმოწერამდე შეამოწმეთ მონაცემები; "
    "საჭიროების შემთხვევაში მიმართეთ იურისტს.",
    "ru": "Это образец договора. Перед подписанием проверьте данные; "
    "при необходимости обратитесь к юристу.",
    "en": "This is a sample agreement. Check all details before signing; "
    "consult a lawyer if needed.",
}


def _money(amount: Decimal, currency: str, language: str) -> str:
    name = _CURRENCY.get(currency, {}).get(language, currency)
    value = f"{amount:,.0f}".replace(",", " ")
    return f"{value} {name}"


def _utilities(value: Utilities, language: str) -> str:
    texts = {
        Utilities.TENANT: {
            "ka": "კომუნალურ გადასახადებს (ელექტროენერგია, გაზი, წყალი, დასუფთავება, "
            "ინტერნეტი) იხდის დამქირავებელი მრიცხველის ჩვენების მიხედვით.",
            "ru": "Коммунальные платежи (электричество, газ, вода, уборка, интернет) "
            "оплачивает Арендатор по показаниям счётчиков.",
            "en": "Utilities (electricity, gas, water, cleaning, internet) are paid by "
            "the Tenant according to the meters.",
        },
        Utilities.LANDLORD: {
            "ka": "კომუნალურ გადასახადებს იხდის გამქირავებელი.",
            "ru": "Коммунальные платежи оплачивает Арендодатель.",
            "en": "Utilities are paid by the Landlord.",
        },
        Utilities.INCLUDED: {
            "ka": "კომუნალური გადასახადები შედის ქირის თანხაში.",
            "ru": "Коммунальные платежи включены в арендную плату.",
            "en": "Utilities are included in the rent.",
        },
    }
    return texts[value][language]


def _person(name: str, document: str, language: str) -> str:
    if not document:
        return name
    label = {"ka": "პირადი ნომერი / პასპორტი", "ru": "паспорт / ID", "en": "passport / ID"}
    return f"{name} ({label[language]}: {document})"


def _clauses(data: ContractData, lang: str) -> list[str]:
    """Пункты договора на одном языке (порядок одинаковый для всех языков)."""
    end_months = data.months
    start = data.start.strftime("%d.%m.%Y")
    landlord = _person(data.landlord_name, data.landlord_id, lang)
    tenant = _person(data.tenant_name, data.tenant_id, lang)
    rent = _money(data.rent, data.currency, lang)
    deposit = _money(data.deposit, data.currency, lang)
    code = city_of(data.city)
    city = city_name(code, lang) if code else data.city
    area = f"{data.area:g}"
    if lang == "ka":
        clauses = [
            f"1. მხარეები. გამქირავებელი: {landlord}. დამქირავებელი: {tenant}.",
            f"2. ხელშეკრულების საგანი. გამქირავებელი გადასცემს დამქირავებელს დროებით "
            f"სარგებლობაში საცხოვრებელ ბინას მისამართზე: ქ. {city}, {data.address}; "
            f"ოთახები: {data.rooms}, ფართი: {area} მ².",
            f"3. ვადა. ხელშეკრულება მოქმედებს {start}-დან {end_months} თვის განმავლობაში.",
            f"4. ქირა. ყოველთვიური ქირის ოდენობა: {rent}. ქირა გადაიხდება ყოველი თვის "
            f"{data.payment_day} რიცხვამდე.",
            f"5. დეპოზიტი. დამქირავებელი იხდის დეპოზიტს. დეპოზიტის ოდენობა: {deposit}. "
            "დეპოზიტი ბრუნდება ხელშეკრულების დასრულებისას, მიყენებული ზიანის და გადაუხდელი "
            "გადასახადების გამოკლებით.",
            f"6. კომუნალური გადასახადები. {_utilities(data.utilities, lang)}",
            "7. შინაური ცხოველები. "
            + (
                "შინაური ცხოველების ყოლა ნებადართულია."
                if data.pets_allowed
                else "შინაური ცხოველების ყოლა დაუშვებელია გამქირავებლის წერილობითი "
                "თანხმობის გარეშე."
            ),
            "8. დამქირავებლის ვალდებულებები. გაუფრთხილდეს ბინას და ქონებას; არ გადასცეს "
            "ბინა ქვექირავნობით გამქირავებლის თანხმობის გარეშე; ხელშეკრულების "
            "დასრულებისას დააბრუნოს ბინა იმავე მდგომარეობაში, ბუნებრივი ცვეთის "
            "გათვალისწინებით.",
            "9. გამქირავებლის ვალდებულებები. გადასცეს ბინა საცხოვრებლად ვარგის "
            "მდგომარეობაში; არ შევიდეს ბინაში დამქირავებლის წინასწარი გაფრთხილების "
            "გარეშე, გარდა საგანგებო შემთხვევისა.",
            "10. შეწყვეტა. თითოეულ მხარეს შეუძლია ხელშეკრულების ვადამდე შეწყვეტა მეორე "
            "მხარისთვის არანაკლებ 30 დღით ადრე წერილობითი შეტყობინებით.",
            "11. დავები. ხელშეკრულება რეგულირდება საქართველოს კანონმდებლობით. დავები "
            "წყდება მოლაპარაკებით, შეთანხმების მიუღწევლობისას — საქართველოს სასამართლოში.",
        ]
        notes = "12. დამატებითი პირობები. " if data.notes else ""
    elif lang == "ru":
        clauses = [
            f"1. Стороны. Арендодатель: {landlord}. Арендатор: {tenant}.",
            f"2. Предмет договора. Арендодатель передаёт Арендатору во временное "
            f"пользование жилую квартиру по адресу: г. {city}, {data.address}; "
            f"комнат: {data.rooms}, площадь: {area} м².",
            f"3. Срок. Договор действует с {start} в течение {end_months} мес.",
            f"4. Арендная плата. Ежемесячная плата составляет {rent} и вносится до "
            f"{data.payment_day} числа каждого месяца.",
            f"5. Депозит. Арендатор вносит депозит в размере {deposit}. Депозит "
            "возвращается по окончании договора за вычетом причинённого ущерба и "
            "неоплаченных платежей.",
            f"6. Коммунальные платежи. {_utilities(data.utilities, lang)}",
            "7. Домашние животные. "
            + (
                "Проживание с домашними животными разрешено."
                if data.pets_allowed
                else "Проживание с домашними животными не допускается без письменного "
                "согласия Арендодателя."
            ),
            "8. Обязанности Арендатора. Бережно относиться к квартире и имуществу; не "
            "сдавать квартиру в субаренду без согласия Арендодателя; по окончании договора "
            "вернуть квартиру в том же состоянии с учётом естественного износа.",
            "9. Обязанности Арендодателя. Передать квартиру в пригодном для проживания "
            "состоянии; не входить в квартиру без предварительного уведомления Арендатора, "
            "кроме аварийных случаев.",
            "10. Расторжение. Каждая сторона может досрочно расторгнуть договор, письменно "
            "уведомив другую сторону не менее чем за 30 дней.",
            "11. Споры. Договор регулируется законодательством Грузии. Споры решаются "
            "переговорами, а при недостижении согласия — в суде Грузии.",
        ]
        notes = "12. Дополнительные условия. " if data.notes else ""
    else:
        clauses = [
            f"1. Parties. Landlord: {landlord}. Tenant: {tenant}.",
            f"2. Subject. The Landlord lets to the Tenant a residential apartment at: "
            f"{city}, {data.address}; rooms: {data.rooms}, area: {area} m².",
            f"3. Term. The agreement is valid from {start} for {end_months} months.",
            f"4. Rent. The monthly rent is {rent}, payable by day {data.payment_day} "
            "of each month.",
            f"5. Deposit. The Tenant pays a deposit of {deposit}. The deposit is returned "
            "at the end of the agreement minus any damage and unpaid charges.",
            f"6. Utilities. {_utilities(data.utilities, lang)}",
            "7. Pets. "
            + (
                "Pets are allowed."
                if data.pets_allowed
                else "Pets are not allowed without the Landlord's written consent."
            ),
            "8. Tenant's obligations. Take care of the apartment and property; not "
            "sublet without the Landlord's consent; return the apartment in the same "
            "condition at the end, allowing for normal wear and tear.",
            "9. Landlord's obligations. Hand over the apartment fit for living; not "
            "enter without prior notice to the Tenant, except in emergencies.",
            "10. Termination. Either party may terminate early with at least 30 days' "
            "written notice to the other party.",
            "11. Disputes. The agreement is governed by the laws of Georgia. Disputes are "
            "settled by negotiation, otherwise by the courts of Georgia.",
        ]
        notes = "12. Additional terms. " if data.notes else ""
    if notes:
        clauses.append(notes + data.notes)
    return clauses


def contract_clauses(data: ContractData, second_language: str) -> list[tuple[str, str]]:
    """Пары пунктов (грузинский, второй язык) — строки таблицы в PDF."""
    if second_language not in SECOND_LANGUAGES:
        raise ValueError(f"second language must be one of {SECOND_LANGUAGES}")
    return list(zip(_clauses(data, "ka"), _clauses(data, second_language), strict=True))


def signature_labels(second_language: str) -> tuple[tuple[str, str], tuple[str, str]]:
    """Подписи сторон: (ka, второй язык) для арендодателя и арендатора."""
    other = {
        "ru": ("Арендодатель", "Арендатор"),
        "en": ("Landlord", "Tenant"),
    }[second_language]
    return ("გამქირავებელი", other[0]), ("დამქირავებელი", other[1])
