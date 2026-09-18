import re

import structlog

from src.bina.application.ports.scraper import RawListing

logger = structlog.get_logger(__name__)


class ListingNormalizer:
    """Нормализатор объявлений."""

    # Маппинг районов Тбилиси на англоязычные названия для унификации
    DISTRICT_MAPPING = {
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
        """Нормализует цену к GEL по приблизительному курсу."""
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
            logger.warning("Missing required fields", source_id=listing.source_id, source_name=listing.source_name)
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
        normalized_price, normalized_currency = self.normalize_price(listing.price, listing.currency)

        # Очистка текста
        normalized_title = self.clean_text(listing.title)
        normalized_description = self.clean_text(listing.description)
        normalized_district = self.normalize_district(listing.district)

        # Обновляем объявление
        normalized_listing = RawListing(
            source_id=listing.source_id,
            source_name=listing.source_name,
            title=normalized_title,
            description=normalized_description,
            price=normalized_price,
            currency=normalized_currency,
            rooms=listing.rooms,
            area=listing.area,
            district=normalized_district,
            url=listing.url,
            photos=listing.photos,
        )

        return normalized_listing
