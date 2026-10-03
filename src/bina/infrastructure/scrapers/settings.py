import os
from dataclasses import dataclass
from typing import ClassVar

from bina.application.cities import parse_cities

DEFAULT_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36",
]


class ScraperSettings:
    """Настройки для парсера объявлений."""

    # Интервал между запусками парсинга (в часах). Каждый час: Premium получает новые
    # квартиры быстро (TASK-085); известные объявления парсер не открывает, нагрузка мала
    SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", "1"))

    # Задержка уведомлений бесплатного тарифа, часов (TASK-085)
    FREE_ALERT_DELAY_HOURS = int(os.getenv("FREE_ALERT_DELAY_HOURS", "3"))

    # Через сколько дней объявление, которого не было в списке сайта, проверяется заново
    RECHECK_DAYS = int(os.getenv("RECHECK_DAYS", "3"))

    # Задержка между запросами (в секундах)
    SCRAPE_DELAY_SECONDS = int(os.getenv("SCRAPE_DELAY_SECONDS", "2"))

    # User-Agent для ротации
    SCRAPE_USER_AGENTS = (
        os.getenv("SCRAPE_USER_AGENTS", "").split(",")
        if os.getenv("SCRAPE_USER_AGENTS")
        else list(DEFAULT_USER_AGENTS)
    )

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


# Города, объявления которых собираем (TASK-079): коды из bina.application.cities
# (пустая переменная в .env — как не заданная)
CITIES: tuple[str, ...] = parse_cities(os.getenv("SCRAPE_CITIES") or "all")


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
    # Батуми (TASK-079): номер города 15 проверен через API TNET (TASK-092); если адрес
    # страницы изменится, откройте на myhome.ge аренду квартир в Батуми и скопируйте
    # адрес (с {page} вместо номера страницы) в MYHOME_SEARCH_PATH_BATUMI.
    SEARCH_PATH_BATUMI = (
        os.getenv("MYHOME_SEARCH_PATH_BATUMI")
        or "/ru/nedvizhimost/arenda/kvartira/batumi/"
        "?deal_types=2&real_estate_types=1&currency_id=1&cities=15&page={page}"
    )
    SEARCH_PATHS: ClassVar[dict[str, str]] = {"tbilisi": SEARCH_PATH, "batumi": SEARCH_PATH_BATUMI}
    # Посуточная аренда (TASK-092): deal_types=7. Номер Батуми (cities=15) проверен через
    # API TNET в сентябре 2026; адрес страницы — как у помесячной аренды, с другим deal_types.
    # «-» в переменной — не собирать посуточную аренду с myhome.ge
    DAILY_SEARCH_PATHS: ClassVar[dict[str, str]] = {
        city: path
        for city, path in {
            "tbilisi": os.getenv("MYHOME_DAILY_SEARCH_PATH")
            or "/ru/nedvizhimost/arenda/kvartira/tbilisi/"
            "?deal_types=7&real_estate_types=1&currency_id=1&cities=1&page={page}",
            "batumi": os.getenv("MYHOME_DAILY_SEARCH_PATH_BATUMI")
            or "/ru/nedvizhimost/arenda/kvartira/batumi/"
            "?deal_types=7&real_estate_types=1&currency_id=1&cities=15&page={page}",
        }.items()
        if path != "-"
    }
    MAX_PAGES = int(os.getenv("MYHOME_MAX_PAGES", "20"))
    SELECTORS = MyHomeSelectors()


class SSSettings:
    """URL поиска SS.ge (переопределяются переменными окружения)."""

    BASE_URL = os.getenv("SS_BASE_URL", "https://home.ss.ge")
    # /ru/недвижимость/l/Квартира/Аренда, цены в лари; {page}: номер страницы.
    # Адрес взят с сайта в сентябре 2026.
    SEARCH_PATH = os.getenv(
        "SS_SEARCH_PATH",
        "/ru/%D0%BD%D0%B5%D0%B4%D0%B2%D0%B8%D0%B6%D0%B8%D0%BC%D0%BE%D1%81%D1%82%D1%8C/l"
        "/%D0%9A%D0%B2%D0%B0%D1%80%D1%82%D0%B8%D1%80%D0%B0/%D0%90%D1%80%D0%B5%D0%BD%D0%B4%D0%B0"
        "?currencyId=1&page={page}",
    )
    # Посуточная аренда (TASK-092): /ru/недвижимость/l/Квартира/Аренда--за-день;
    # «-» — не собирать
    DAILY_SEARCH_PATH = os.getenv(
        "SS_DAILY_SEARCH_PATH",
        "/ru/%D0%BD%D0%B5%D0%B4%D0%B2%D0%B8%D0%B6%D0%B8%D0%BC%D0%BE%D1%81%D1%82%D1%8C/l"
        "/%D0%9A%D0%B2%D0%B0%D1%80%D1%82%D0%B8%D1%80%D0%B0/%D0%90%D1%80%D0%B5%D0%BD%D0%B4%D0%B0"
        "--%D0%B7%D0%B0-%D0%B4%D0%B5%D0%BD%D1%8C?currencyId=1&page={page}",
    )
    MAX_PAGES = int(os.getenv("SS_MAX_PAGES", "20"))


class LivoSettings:
    """Livo.ge (TASK-092): сайт TNET, объявления берутся из его API (как на самом сайте)."""

    BASE_URL = os.getenv("LIVO_BASE_URL", "https://livo.ge")
    API_URL = os.getenv("LIVO_API_URL", "https://api-statements.tnet.ge")
    # Ключ сайта в заголовке X-Website-Key: без него API отвечает 403 (виден в коде сайта)
    WEBSITE_KEY = os.getenv("LIVO_WEBSITE_KEY", "livo")
    # Квартиры (real_estate_types=1), аренда помесячно и посуточно (deal_types=2,7);
    # города — cities=1,15 (Тбилиси, Батуми) из SCRAPE_CITIES; {page}: номер страницы
    SEARCH_QUERY = os.getenv(
        "LIVO_SEARCH_QUERY", "deal_types=2,7&real_estate_types=1&cities={cities}&page={page}"
    )
    MAX_PAGES = int(os.getenv("LIVO_MAX_PAGES", "20"))


class KorterSettings:
    """Korter.ge (TASK-092): данные объявлений лежат в странице (``window.INITIAL_STATE``)."""

    BASE_URL = os.getenv("KORTER_BASE_URL", "https://korter.ge")
    # Город → адрес раздела аренды квартир (из sitemap сайта, сентябрь 2026); {page}: страница
    SEARCH_PATHS: ClassVar[dict[str, str]] = {
        "tbilisi": os.getenv("KORTER_SEARCH_PATH")
        or "/ru/%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B0-%D0%BA%D0%B2%D0%B0%D1%80%D1%82%D0%B8%D1%80-"
        "%D1%82%D0%B1%D0%B8%D0%BB%D0%B8%D1%81%D0%B8?page={page}",
        "batumi": os.getenv("KORTER_SEARCH_PATH_BATUMI")
        or "/ru/%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B0-%D0%BA%D0%B2%D0%B0%D1%80%D1%82%D0%B8%D1%80-"
        "%D0%B1%D0%B0%D1%82%D1%83%D0%BC%D0%B8?page={page}",
    }
    # Посуточная аренда: «аренда-квартир-посуточно-<город>»
    DAILY_SEARCH_PATHS: ClassVar[dict[str, str]] = {
        "tbilisi": os.getenv("KORTER_DAILY_SEARCH_PATH")
        or "/ru/%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B0-%D0%BA%D0%B2%D0%B0%D1%80%"
        "D1%82%D0%B8%D1%80-%D0%BF%D0%BE%D1%81%D1%83%D1%82%D0%BE%D1%87%D0%BD%D0%BE-%D1%82%D0%B1%D0%B8%D0%BB%D0%B8%D1%81%D0%B8?page={page}",
        "batumi": os.getenv("KORTER_DAILY_SEARCH_PATH_BATUMI")
        or "/ru/%D0%B0%D1%80%D0%B5%D0%BD%D0%B4%D0%B0-%D0%BA%D0%B2%D0%B0%D1%80%"
        "D1%82%D0%B8%D1%80-%D0%BF%D0%BE%D1%81%D1%83%D1%82%D0%BE%D1%87%D0%BD%D0%BE-%D0%B1%D0%B0%D1%82%D1%83%D0%BC%D0%B8?page={page}",
    }
    MAX_PAGES = int(os.getenv("KORTER_MAX_PAGES", "20"))


# Публичные каналы с арендой в Тбилиси (веб-версия t.me/s/...); группы так не читаются
DEFAULT_TELEGRAM_CHANNELS = (
    "Forrentge",
    "m2tbilis",
    "kvartiry_tbilisi_ge",
    "nestydnye_kvartiry_tbilisi",
    "tbilisi_kvartiry",
    "kvartiry_tbilisi_arenda",
    "kvartiry_tbili_city",
    "ApartameniTbilisi",
    "kvartiry_v_tbilisii",
)


class TelegramSettings:
    """Telegram-каналы как источник объявлений (TASK-091)."""

    BASE_URL = os.getenv("TELEGRAM_BASE_URL", "https://t.me")
    # Через запятую; пусто — список по умолчанию, "-" — не читать каналы
    CHANNELS: tuple[str, ...] = tuple(
        name.strip().lstrip("@")
        for name in (os.getenv("TELEGRAM_CHANNELS") or ",".join(DEFAULT_TELEGRAM_CHANNELS)).split(
            ","
        )
        if name.strip() and name.strip() != "-"
    )
    # Страниц (по ~20 постов) с канала за запуск и возраст постов, которые берём
    MAX_PAGES = int(os.getenv("TELEGRAM_MAX_PAGES", "5"))
    MAX_AGE_DAYS = int(os.getenv("TELEGRAM_MAX_AGE_DAYS", "21"))
    # Город каналов по умолчанию; посты про другие города из SCRAPE_CITIES тоже берутся
    CITY = os.getenv("TELEGRAM_CITY", "Tbilisi")
