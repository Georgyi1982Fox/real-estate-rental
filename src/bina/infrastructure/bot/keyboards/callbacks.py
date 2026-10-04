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
    # Проверка собственника (TASK-098): request — заявка
    VERIFY_OK = "vok"
    VERIFY_NO = "vno"
    # Блокировка агентства (TASK-100): request — агентство
    AGENCY_BLOCK = "ablk"


class AdminCallback(CallbackData, prefix="adm"):
    action: AdminAction
    listing: UUID | None = None
    request: UUID | None = None


class OwnerAction(StrEnum):
    """Размещение и управление объявлениями собственника (TASK-096)."""

    LIST = "list"
    NEW = "new"
    CITY = "city"
    PERIOD = "per"
    ROOMS = "rooms"
    SKIP_FLOOR = "nofl"
    SKIP_LOCATION = "noloc"
    PHOTOS_DONE = "phok"
    PUBLISH = "pub"
    CANCEL = "cncl"
    OFF = "off"
    ON = "on"
    PRICE = "price"
    PROMOTE = "top"  # TASK-097: «🔥 Топ» за звёзды
    VERIFY = "ver"  # TASK-098: прислать документ собственника


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


class ChatAction(StrEnum):
    """Чат с хозяином и просмотры (TASK-111, TASK-112)."""

    OPEN = "o"  # id — объявление: карточка с кнопками
    WRITE = "w"  # id — объявление: написать хозяину
    REPLY = "r"  # id — диалог: ответить
    VIEW = "v"  # id — объявление: выбрать день просмотра
    DAY = "d"  # id — объявление, day: выбрать час
    TIME = "t"  # id — объявление, day, hour: отправить просьбу
    CONFIRM = "y"  # id — просмотр: хозяин подтверждает
    DECLINE = "n"  # id — просмотр: хозяин отказывает


class ChatCallback(CallbackData, prefix="ch"):
    """``day`` — дата ``ГГГГММДД``, ``hour`` — час начала просмотра."""

    action: ChatAction
    id: UUID
    day: int = 0
    hour: int = 0


class AgencyAction(StrEnum):
    """Кабинет риелтора / агентства (TASK-100)."""

    JOIN = "j"  # «💼 Я риелтор / агентство» — регистрация
    CABINET = "c"  # кабинет: пакет, лимит, статистика
    PLANS = "p"  # пакеты объявлений
    BUY = "b"  # value — пакет: счёт в звёздах
    BUMP = "u"  # listing — «⭐ Premium-объявление»


class AgencyCallback(CallbackData, prefix="ag"):
    action: AgencyAction
    value: str | None = None
    listing: UUID | None = None


class AccountAction(StrEnum):
    """Свои данные (TASK-059, TASK-060) — в профиле."""

    EXPORT = "e"  # прислать файл со всеми данными
    ASK_DELETE = "d"  # спросить: точно удалить?
    DELETE = "y"  # удалить всё
    CANCEL = "n"


class AccountCallback(CallbackData, prefix="acc"):
    action: AccountAction


class RecommendCallback(CallbackData, prefix="rec"):
    """«✨ Вам может понравиться» под избранным (TASK-076)."""


class SignAction(StrEnum):
    """Подпись документов (TASK-115)."""

    SIGN = "s"
    DECLINE = "d"
    OPEN = "o"  # прислать свой документ ещё раз (и сертификат, если подписан)
    LIST = "l"  # «📄 Мои документы» в профиле


class SignCallback(CallbackData, prefix="sg"):
    action: SignAction
    id: UUID | None = None
