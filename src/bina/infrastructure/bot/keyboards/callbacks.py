"""Фабрики callback data.

Состояние поиска целиком кодируется в callback data, поэтому кнопки работают
без FSM-хранилища и переживают перезапуск бота. Лимит Telegram: 64 байта.
"""

from enum import StrEnum
from uuid import UUID

from aiogram.filters.callback_data import CallbackData


class SearchStep(StrEnum):
    """Шаг мастера поиска."""

    CITY = "c"
    DISTRICT = "d"
    PRICE = "p"
    ROOMS = "r"
    RESULTS = "res"


# ``SearchCallback.period`` посуточной аренды (коротко: лимит callback data 64 байта)
DAILY_PERIOD = "d"


class SearchCallback(CallbackData, prefix="s"):
    """Навигация по мастеру поиска и страницам результатов.

    ``price`` и ``rooms``: индексы пресетов из :mod:`.filters`, ``None``: «любые».
    ``page``: страница списка районов на шаге DISTRICT и страница результатов на RESULTS.
    ``city``: код города (TASK-079); ``None`` — все города.
    ``period``: ``d`` — посуточная аренда (TASK-092), ``None`` — помесячная.
    """

    step: SearchStep
    district: UUID | None = None
    price: int | None = None
    rooms: int | None = None
    page: int = 0
    city: str | None = None
    period: str | None = None

    @property
    def daily(self) -> bool:
        return self.period == DAILY_PERIOD


class FavoriteToggleCallback(CallbackData, prefix="fav"):
    """Добавить объявление в избранное или убрать из него."""

    listing_id: UUID


class FavoritesPageCallback(CallbackData, prefix="favp"):
    """Страница избранного."""

    page: int


class LanguageCallback(CallbackData, prefix="lang"):
    """Смена языка интерфейса."""

    code: str


class NoopCallback(CallbackData, prefix="noop"):
    """Неактивная кнопка (счётчик страниц)."""


class PremiumBuyCallback(CallbackData, prefix="buy"):
    """Купить тариф (прислать счёт в звёздах)."""

    plan: str


class RentAction(StrEnum):
    """Действие с напоминаниями об оплате аренды (TASK-109)."""

    ADD = "add"
    DAY = "day"
    DELETE = "del"
    PAID = "paid"


class RentCallback(CallbackData, prefix="rent"):
    """``day`` — день месяца при добавлении; ``due`` — дата оплаты ``YYYYMMDD`` для «Оплачено»."""

    action: RentAction
    reminder: UUID | None = None
    day: int | None = None
    due: str | None = None


class AdminAction(StrEnum):
    """Действия админки (TASK-110)."""

    STATS = "stats"
    COMPLAINTS = "compl"
    HIDE = "hide"
    RESTORE = "restore"


class AdminCallback(CallbackData, prefix="adm"):
    action: AdminAction
    listing: UUID | None = None


class OwnerAction(StrEnum):
    """Размещение и управление объявлениями собственника (TASK-096)."""

    LIST = "list"
    NEW = "new"
    CITY = "city"
    PERIOD = "per"
    ROOMS = "rooms"
    SKIP_FLOOR = "nofl"
    PHOTOS_DONE = "phok"
    PUBLISH = "pub"
    CANCEL = "cncl"
    OFF = "off"
    ON = "on"
    PRICE = "price"


class OwnerCallback(CallbackData, prefix="own"):
    """``value`` — выбор на шаге мастера; ``listing`` — своё объявление."""

    action: OwnerAction
    value: str | None = None
    listing: UUID | None = None


class MenuSection(StrEnum):
    """Кнопки главного меню бота."""

    HOME = "home"
    SEARCH = "search"
    SMART = "smart"
    DAILY = "daily"
    OWNER = "owner"
    FAVORITES = "fav"
    PREMIUM = "premium"
    INVITE = "invite"
    RENT = "rent"
    PROFILE = "profile"
    HELP = "help"
    SUPPORT = "support"
    TERMS = "terms"
    PRIVACY = "privacy"
    ADMIN = "admin"


class MenuCallback(CallbackData, prefix="m"):
    section: MenuSection
