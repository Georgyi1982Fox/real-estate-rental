import dataclasses
import re
from typing import ClassVar

import structlog

from bina.application.cities import CITIES, city_in_text
from bina.application.ports.scraper import RawListing
from bina.application.rent_period import (
    AREA_PER_ROOM_FIXED_MAX,
    AREA_PER_ROOM_MAX,
    DAILY_PRICE_MAX_GEL,
    MONTHLY_PRICE_MIN_GEL,
    PRICE_MIN_GEL,
    RENT_MAX_GEL,
    RENT_PER_M2_MAX_GEL,
)
from bina.application.text import html_to_text

logger = structlog.get_logger(__name__)

# Сколько первых символов описания смотреть, ища город («Сдаётся квартира в Батуми»)
CITY_HEAD_CHARS = 200


# Символы валют → коды
CURRENCY_SYMBOLS = {"₾": "GEL", "$": "USD", "€": "EUR"}


class ListingNormalizer:
    """Нормализатор объявлений."""

    # Маппинг районов Тбилиси на англоязычные названия для унификации
    DISTRICT_MAPPING: ClassVar[dict[str, str]] = {
        # MyHome.ge и SS.ge могут использовать разные названия
        "ვაკე": "Vake",
        "ვაჟის უბანი": "Vazisubani",
        "საბურთალო": "Saburtalo",
        "ისანი": "Isani",
        "ჩუღურეთი": "Chughureti",
        "მთაწმინდა": "Mtatsminda",
        "გლდანი": "Gldani",
        "სამგორი": "Samgori",
        "კრწანისი": "Krtsanisi",
        "ნაძალადევი": "Nadzaladevi",
        "ვაკის რაიონი": "Vake",
        "საბურთალოს რაიონი": "Saburtalo",
        "ისნის რაიონი": "Isani",
        # Добавим английские варианты
        "Vake": "Vake",
        "Vazisubani": "Vazisubani",
        "Saburtalo": "Saburtalo",
        "Isani": "Isani",
        "Chughureti": "Chughureti",
        "Mtatsminda": "Mtatsminda",
        "Gldani": "Gldani",
        "Samgori": "Samgori",
        "Krtsanisi": "Krtsanisi",
        "Nadzaladevi": "Nadzaladevi",
        # Прочие возможные варианты
        "Unknown": "Unknown",
        "": "Unknown",
    }

    @staticmethod
    def normalize_price(price: float, currency: str) -> tuple[float, str]:
        """Нормализует цену к GEL по приблизительному курсу.

        Валюта — код (``GEL``, ``USD``, ``EUR``) или символ (``₾``, ``$``, ``€``).
        """
        currency = CURRENCY_SYMBOLS.get(currency.strip(), currency.strip())
        if currency.upper() == "GEL":
            return price, "GEL"
        elif currency.upper() == "USD":
            # Приблизительный курс USD to GEL (реальный курс нужно получать из API)
            usd_to_gel_rate = 2.7
            return price * usd_to_gel_rate, "GEL"
        elif currency.upper() == "EUR":
            # Приблизительный курс EUR to GEL
            eur_to_gel_rate = 3.0
            return price * eur_to_gel_rate, "GEL"
        else:
            # Неизвестная валюта - оставляем как есть
            logger.warning("Unknown currency", currency=currency)
            return price, currency

    @staticmethod
    def clean_text(text: str) -> str:
        """Очищает текст от лишних символов и нормализует пробелы."""
        if not text:
            return ""

        # Удаляем лишние пробелы и переносы строк
        text = re.sub(r"\s+", " ", text)
        # Удаляем специальные символы в начале и конце
        text = text.strip(" \t\n\r\f\v.,;:!?")
        return text

    @staticmethod
    def clean_multiline(text: str) -> str:
        """Как :meth:`clean_text`, но сохраняет переносы строк (абзацы описания)."""
        if not text:
            return ""
        text = html_to_text(text)
        lines = [re.sub(r"[ \t\f\v\r]+", " ", line).strip() for line in text.split("\n")]
        # Не больше одной пустой строки подряд
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
        return text.strip()

    @classmethod
    def normalize_district(cls, district: str) -> str:
        """Нормализует название района."""
        if not district:
            return "Unknown"

        # Очищаем текст
        clean_district = cls.clean_text(district)

        # Приводим к нижнему регистру для сравнения
        district_lower = clean_district.lower()

        # Ищем совпадение в маппинге
        for georgian_name, normalized_name in cls.DISTRICT_MAPPING.items():
            if georgian_name.lower() == district_lower:
                return normalized_name

        # Если не найдено точное совпадение, возвращаем очищенное название
        return clean_district

    @staticmethod
    def validate_fields(listing: RawListing) -> bool:
        """Валидирует поля объявления."""
        # Проверяем обязательные поля
        if not listing.source_id or not listing.source_name:
            logger.warning(
                "Missing required fields",
                source_id=listing.source_id,
                source_name=listing.source_name,
            )
            return False

        # Проверяем числовые поля
        if listing.price <= 0:
            logger.warning("Invalid price", price=listing.price, source_id=listing.source_id)
            return False

        if listing.rooms <= 0:
            logger.warning("Invalid rooms", rooms=listing.rooms, source_id=listing.source_id)
            return False

        if listing.area <= 0:
            logger.warning("Invalid area", area=listing.area, source_id=listing.source_id)
            return False

        return True

    def normalize_listing(self, listing: RawListing) -> RawListing | None:
        """Нормализует объявление."""
        # Валидация
        if not self.validate_fields(listing):
            return None

        # Нормализация цены
        normalized_price, normalized_currency = self.normalize_price(
            listing.price, listing.currency
        )

        # Очистка текста
        normalized_title = self.clean_text(listing.title)
        normalized_description = self.clean_multiline(listing.description)
        normalized_district = self.normalize_district(listing.district)

        # Остальные поля (фото, телефон, имя, язык) сохраняются как есть
        normalized = dataclasses.replace(
            listing,
            title=normalized_title,
            description=normalized_description,
            price=normalized_price,
            currency=normalized_currency,
            district=normalized_district,
            descriptions={
                code: text
                for code, value in listing.descriptions.items()
                if (text := self.clean_multiline(value))
            },
        )
        fixed = self.fix_area(self.fix_rent_period(self.fix_city(normalized)))
        if not self.rent_price_possible(fixed):
            logger.warning(
                "Rent price looks like a sale price, listing skipped",
                source=fixed.source_name,
                source_id=fixed.source_id,
                price=fixed.price,
                area=fixed.area,
            )
            return None
        return fixed

    @staticmethod
    def rent_price_possible(listing: RawListing) -> bool:
        """Цена похожа на аренду: не 325 000 ₾ в месяц за 70 м² (продажа) и не «1 ₾»."""
        if listing.currency != "GEL":
            return True
        if listing.price < PRICE_MIN_GEL:
            return False
        if listing.rent_period != "monthly":
            return True
        if listing.area > 0:
            return listing.price / listing.area <= RENT_PER_M2_MAX_GEL
        return listing.price <= RENT_MAX_GEL

    @staticmethod
    def fix_rent_period(listing: RawListing) -> RawListing:
        """Вид аренды по цене, когда хозяин ошибся на сайте.

        «Посуточно» за 1 000+ ₾ в сутки — цена за месяц; «помесячно» за 20-149 ₾ — цена
        за сутки (Бакуриани: 60 ₾).
        """
        if listing.currency != "GEL":
            return listing
        if listing.rent_period == "daily" and listing.price > DAILY_PRICE_MAX_GEL:
            return dataclasses.replace(listing, rent_period="monthly")
        if (
            listing.rent_period == "monthly"
            and PRICE_MIN_GEL <= listing.price < MONTHLY_PRICE_MIN_GEL
        ):
            return dataclasses.replace(listing, rent_period="daily")
        return listing

    @staticmethod
    def fix_area(listing: RawListing) -> RawListing:
        """Лишний ноль в площади: 4 комнаты на 1 400 м² — это 140 м²."""
        if listing.rooms <= 0 or listing.area <= AREA_PER_ROOM_MAX * listing.rooms:
            return listing
        smaller = listing.area / 10
        if smaller > AREA_PER_ROOM_FIXED_MAX * listing.rooms:
            return listing  # и без нуля слишком много — оставляем как есть
        return dataclasses.replace(listing, area=smaller)

    @staticmethod
    def fix_city(listing: RawListing) -> RawListing:
        """Квартира в другом городе, чем раздел сайта: «Сдаётся квартира в Батуми» в Тбилиси.

        Агентства выкладывают объявления не в тот город (Korter.ge: батумские квартиры в
        разделе Тбилиси). Если текст называет ровно один другой город — квартира переносится
        туда: район — сам город, точка на карте (она в чужом городе) убирается.
        """
        # Только начало описаний («Сдаётся квартира в …»): дальше бывает «выезд в Мцхета»
        heads = [
            text[:CITY_HEAD_CHARS] for text in [listing.description, *listing.descriptions.values()]
        ]
        named = city_in_text("\n".join([listing.title, *heads]))
        if named is None or named == listing.city:
            return listing
        logger.info(
            "Listing moved to the city named in its text",
            source=listing.source_name,
            source_id=listing.source_id,
            from_city=listing.city,
            to_city=named,
        )
        return dataclasses.replace(
            listing,
            city=named,
            district=CITIES[named].names["ru"],
            latitude=None,
            longitude=None,
        )
