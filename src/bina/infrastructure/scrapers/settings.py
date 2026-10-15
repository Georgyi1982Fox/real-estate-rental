import os
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import quote

from bina.application.cities import CITIES as CITY_INFO
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

# Крупные города с рынком аренды — для сайтов MyHome и Korter, где раздел задаётся
# адресом по городу (TASK-079/092). Берём города с номером TNET: Тбилиси, Батуми,
# Кутаиси, Рустави, Поти, Кобулети. Остальные города собирают ss.ge (весь список по адресу
# объявления) и livo.ge. Адреса проверены на сайтах в октябре 2026.
MAJOR_CITIES: tuple[str, ...] = tuple(
    code for code, info in CITY_INFO.items() if info.tnet_city_id is not None
)


def _with_overrides(paths: dict[str, str], overrides: dict[str, str | None]) -> dict[str, str]:
    """Переопределения из .env: значение — адрес вместо сгенерированного, «-» — не собирать."""
    result = dict(paths)
    for code, value in overrides.items():
        if value == "-":
            result.pop(code, None)
        elif value:
            result[code] = value
    return result


def _myhome_paths(deal_types: int) -> dict[str, str]:
    """Аренда квартир MyHome по крупным городам: slug — код города, фильтр ``cities=<номер TNET>``.

    ``deal_types``: 2 — помесячная аренда, 7 — посуточная.
    """
    return {
        code: (
            f"/ru/nedvizhimost/arenda/kvartira/{code}/?deal_types={deal_types}"
            f"&real_estate_types=1&currency_id=1&cities={CITY_INFO[code].tnet_city_id}&page={{page}}"
        )
        for code in MAJOR_CITIES
    }


def _korter_paths(daily: bool) -> dict[str, str]:
    """Аренда квартир Korter по крупным городам: адрес из русского названия города.

    Помесячно — «аренда-квартир-<город>», посуточно — «аренда-квартир-посуточно-<город>».
    """
    prefix = "аренда-квартир-посуточно-" if daily else "аренда-квартир-"
    return {
        code: f"/ru/{quote(prefix + CITY_INFO[code].names['ru'].lower())}?page={{page}}"
        for code in MAJOR_CITIES
    }


class MyHomeSettings:
    """URL и селекторы MyHome.ge (переопределяются переменными окружения)."""

    BASE_URL = os.getenv("MYHOME_BASE_URL", "https://www.myhome.ge")
    # Помесячная аренда квартир по крупным городам (TASK-079/092): slug — код города,
    # фильтр cities=<номер TNET>, GEL, {page} — номер страницы. Адрес проверен в октябре 2026.
    # MYHOME_SEARCH_PATH / MYHOME_SEARCH_PATH_BATUMI переопределяют Тбилиси и Батуми,
    # «-» — не собирать город.
    SEARCH_PATHS: ClassVar[dict[str, str]] = _with_overrides(
        _myhome_paths(2),
        {
            "tbilisi": os.getenv("MYHOME_SEARCH_PATH"),
            "batumi": os.getenv("MYHOME_SEARCH_PATH_BATUMI"),
        },
    )
    # Посуточная аренда (TASK-092): deal_types=7; «-» в переменной — не собирать город.
    DAILY_SEARCH_PATHS: ClassVar[dict[str, str]] = _with_overrides(
        _myhome_paths(7),
        {
            "tbilisi": os.getenv("MYHOME_DAILY_SEARCH_PATH"),
            "batumi": os.getenv("MYHOME_DAILY_SEARCH_PATH_BATUMI"),
        },
    )
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
    # Город → адрес раздела аренды квартир из русского названия города (TASK-092);
    # {page} — номер страницы. KORTER_SEARCH_PATH / _BATUMI переопределяют Тбилиси и Батуми,
    # «-» — не собирать город. Адреса проверены на сайте в октябре 2026.
    SEARCH_PATHS: ClassVar[dict[str, str]] = _with_overrides(
        _korter_paths(daily=False),
        {
            "tbilisi": os.getenv("KORTER_SEARCH_PATH"),
            "batumi": os.getenv("KORTER_SEARCH_PATH_BATUMI"),
        },
    )
    # Посуточная аренда: «аренда-квартир-посуточно-<город>»
    DAILY_SEARCH_PATHS: ClassVar[dict[str, str]] = _with_overrides(
        _korter_paths(daily=True),
        {
            "tbilisi": os.getenv("KORTER_DAILY_SEARCH_PATH"),
            "batumi": os.getenv("KORTER_DAILY_SEARCH_PATH_BATUMI"),
        },
    )
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
