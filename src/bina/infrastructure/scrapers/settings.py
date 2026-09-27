import os
from dataclasses import dataclass


class ScraperSettings:
    """Настройки для парсера объявлений."""

    # Интервал между запусками парсинга (в часах)
    SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))

    # Задержка между запросами (в секундах)
    SCRAPE_DELAY_SECONDS = int(os.getenv("SCRAPE_DELAY_SECONDS", "2"))

    # User-Agent для ротации
    SCRAPE_USER_AGENTS = os.getenv("SCRAPE_USER_AGENTS", "").split(",") if os.getenv("SCRAPE_USER_AGENTS") else [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    ]

    # Базовые URL для источников
    MYHOME_BASE_URL = os.getenv("MYHOME_BASE_URL", "https://www.myhome.ge")
    SS_BASE_URL = os.getenv("SS_BASE_URL", "https://ss.ge")


@dataclass(frozen=True)
class MyHomeSelectors:
    """CSS-селекторы MyHome.ge.

    Значения по умолчанию соответствуют фикстурам в
    tests/unit/infrastructure/scrapers/test_data/. Для реального сайта их нужно
    сверить с HTML, сохранённым через ``bina-scrape --source myhome --dump-dir``.
    """

    # Страница списка
    card: str = "[data-listing-id]"
    card_id_attr: str = "data-listing-id"
    card_link: str = ".card-title a"
    card_price: str = ".price-tag"
    card_district: str = ".location, .card-location"
    card_rooms: str = ".info-item.-rooms, .card-rooms"
    card_area: str = ".info-item.-area, .card-area"
    card_description: str = ".description, .card-description"
    card_image: str = "img"
    # Страница объявления
    detail_title: str = "h1"
    detail_price: str = ".price-tag"
    detail_district: str = ".location"
    detail_rooms: str = ".info-item.-rooms"
    detail_area: str = ".info-item.-area"
    detail_description: str = ".description"
    detail_photos: str = ".gallery img"
    detail_phone: str = "[data-phone], .phone"
    detail_owner: str = ".owner-name"


class MyHomeSettings:
    """URL и селекторы MyHome.ge (переопределяются переменными окружения)."""

    BASE_URL = os.getenv("MYHOME_BASE_URL", "https://www.myhome.ge")
    # Аренда (deal_types=2), квартиры (real_estate_types=1), Тбилиси (cities=1), GEL;
    # {page}: номер страницы. Адрес взят с сайта в сентябре 2026.
    SEARCH_PATH = os.getenv(
        "MYHOME_SEARCH_PATH",
        "/ru/nedvizhimost/arenda/kvartira/tbilisi/"
        "?deal_types=2&real_estate_types=1&currency_id=1&cities=1&page={page}",
    )
    MAX_PAGES = int(os.getenv("MYHOME_MAX_PAGES", "20"))
    SELECTORS = MyHomeSelectors()
