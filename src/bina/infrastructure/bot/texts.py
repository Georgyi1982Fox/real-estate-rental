"""Тексты интерфейса бота.

Интерфейс переведён на русский и английский. Для грузинского (``ka``)
интерфейс пока английский, но объявления показываются на грузинском.
"""

from bina.application.use_cases.register_user import DEFAULT_LANGUAGE

_RU: dict[str, str] = {
    "welcome_new": (
        "👋 Добро пожаловать в <b>Bina.ai</b>!\n\n"
        "Я помогу найти жильё в аренду в Грузии: объявления с MyHome.ge и SS.ge "
        "в одном месте, с переводом и проверкой на мошенничество.\n\n"
        "Нажмите «🔍 Поиск», чтобы начать, или /help, чтобы узнать больше."
    ),
    "welcome_back": "👋 С возвращением! Выберите действие в меню ниже.",
    "help": (
        "<b>Bina.ai: аренда жилья в Грузии</b>\n\n"
        "/search: поиск по району, цене и количеству комнат\n"
        "/favorites: избранные объявления\n"
        "/profile: профиль, подписка и язык\n"
        "/premium: Premium-подписка\n"
        "/help: эта справка\n\n"
        "Добавляйте объявления в избранное кнопками ☆ под результатами поиска."
    ),
    "unknown": "Не понял 🤔 Воспользуйтесь меню или командой /help.",
    "error": "⚠️ Что-то пошло не так. Попробуйте ещё раз чуть позже.",
    "menu_search": "🔍 Поиск",
    "menu_favorites": "❤️ Избранное",
    "menu_profile": "👤 Профиль",
    "open_app": "📱 Открыть Bina.ai",
    "back": "⬅️ Назад",
    "new_search": "🔄 Новый поиск",
    "choose_district": "📍 <b>Шаг 1/3.</b> Выберите район:",
    "no_districts": "Районы ещё не загружены. Показываю все объявления.",
    "choose_price": "📍 {district}\n\n💰 <b>Шаг 2/3.</b> Бюджет в месяц:",
    "choose_rooms": "📍 {district} · 💰 {price}\n\n🚪 <b>Шаг 3/3.</b> Количество комнат:",
    "any_district": "Любой район",
    "any_price": "Любая цена",
    "any_rooms": "Любое",
    "price_up_to": "до {max} ₾",
    "price_between": "{min}–{max} ₾",  # noqa: RUF001 (en dash в диапазоне)
    "price_from": "от {min} ₾",
    "rooms_exact": "{n}",
    "rooms_from": "{n}+",
    "rooms_label": "{value} комн.",
    "search_header": "🔍 Найдено: <b>{total}</b>\n📍 {district} · 💰 {price} · 🚪 {rooms}",
    "search_empty": (
        "🔍 По фильтрам ничего не найдено.\n📍 {district} · 💰 {price} · 🚪 {rooms}\n\n"
        "Попробуйте расширить параметры поиска."
    ),
    "page_counter": "Страница {page} из {pages}",
    "listing_rooms": "{n} комн.",
    "listing_area": "{area} м²",
    "fav_hint": "☆/★: добавить или убрать из избранного",
    "favorites_header": "❤️ <b>Избранное</b>: {total}",
    "favorites_empty": "❤️ В избранном пока пусто.\n\nНайдите жильё через «🔍 Поиск» и нажмите ☆.",
    "fav_added": "★ Добавлено в избранное",
    "fav_removed": "☆ Удалено из избранного",
    "listing_unavailable": "Это объявление больше недоступно.",
    "message_outdated": "Сообщение устарело, откройте раздел заново.",
    "profile": (
        "👤 <b>Профиль</b>\n\n"
        "🌐 Язык: {language}\n"
        "⭐ Подписка: {tier}{expires}\n"
        "💳 Баланс: {balance} ₾\n"
        "❤️ В избранном: {favorites}\n"
        "📅 С нами с {since}\n\n"
        "Выберите язык интерфейса:"
    ),
    "subscription_until": " (до {date})",
    "tier_free": "Бесплатная",
    "tier_nomad": "Premium",
    "tier_family": "Family",
    "tier_realtor": "Риелтор",
    "language_changed": "✅ Язык изменён.",
    # TASK-028: уведомления
    "notify_new_listing": "🏠 <b>Новая квартира</b> по поиску «{search}»\n\n{listing}",
    "notify_new_listing_no_search": "🏠 <b>Новая квартира</b> по вашему поиску\n\n{listing}",
    "notify_price_drop": "📉 <b>Цена снижена</b>: {old} → <b>{new}</b>\n\n{listing}",
    "notify_details": "{price} · {rooms} комн. · {area} м²",
    "notify_open": "Открыть",
    # TASK-026/027: подписка Premium
    "premium_info": (
        "⭐ <b>Bina.ai Premium</b>\n\n"
        "{status}\n\n"
        "<b>Бесплатно:</b> избранное без ограничений, {free_searches} сохранённый поиск.\n"
        "<b>Premium:</b> до {premium_searches} сохранённых поисков "
        "с уведомлениями о новых квартирах.\n\n"
        "Цена: <b>{price} ⭐</b> за {days} дн. Оплата звёздами Telegram."
    ),
    "premium_free": "Сейчас у вас бесплатный тариф.",
    "premium_active": "✅ Premium действует до {date}.",
    "premium_buy": "Купить за {price} ⭐",
    "premium_extend": "Продлить на {days} дн. за {price} ⭐",
    "premium_activated": "🎉 Спасибо! Premium действует до {date}.",
    "premium_invoice_outdated": "Счёт устарел. Откройте /premium и попробуйте ещё раз.",
    "premium_payment_problem": (
        "⚠️ Оплата получена, но подписку не удалось включить автоматически. "
        "Напишите в /paysupport, мы всё исправим."
    ),
    "fraud_warning": "Есть признаки мошенничества: не платите до просмотра",
    "fav_limit": (
        "В бесплатном тарифе до {limit} квартир в избранном. "
        "Уберите лишние или подключите Premium: /premium"
    ),
    "paysupport": (
        "💬 <b>Вопросы по оплате</b>\n\n"
        "Если подписка не включилась или нужен возврат звёзд, напишите нам "
        "в ответ на это сообщение: опишите проблему и дату оплаты."
    ),
}

_EN: dict[str, str] = {
    "welcome_new": (
        "👋 Welcome to <b>Bina.ai</b>!\n\n"
        "I'll help you find a rental home in Georgia: listings from MyHome.ge and SS.ge "
        "in one place, translated and checked for fraud.\n\n"
        "Tap “🔍 Search” to start, or /help to learn more."
    ),
    "welcome_back": "👋 Welcome back! Pick an option from the menu below.",
    "help": (
        "<b>Bina.ai: rentals in Georgia</b>\n\n"
        "/search: search by district, price and rooms\n"
        "/favorites: your saved listings\n"
        "/profile: profile, subscription and language\n"
        "/premium: Premium subscription\n"
        "/help: this help\n\n"
        "Save listings with the ☆ buttons under search results."
    ),
    "unknown": "Sorry, I didn't get that 🤔 Use the menu or /help.",
    "error": "⚠️ Something went wrong. Please try again a bit later.",
    "menu_search": "🔍 Search",
    "menu_favorites": "❤️ Favorites",
    "menu_profile": "👤 Profile",
    "open_app": "📱 Open Bina.ai",
    "back": "⬅️ Back",
    "new_search": "🔄 New search",
    "choose_district": "📍 <b>Step 1/3.</b> Choose a district:",
    "no_districts": "Districts are not loaded yet. Showing all listings.",
    "choose_price": "📍 {district}\n\n💰 <b>Step 2/3.</b> Monthly budget:",
    "choose_rooms": "📍 {district} · 💰 {price}\n\n🚪 <b>Step 3/3.</b> Number of rooms:",
    "any_district": "Any district",
    "any_price": "Any price",
    "any_rooms": "Any",
    "price_up_to": "up to {max} ₾",
    "price_between": "{min}–{max} ₾",  # noqa: RUF001 (en dash в диапазоне)
    "price_from": "from {min} ₾",
    "rooms_exact": "{n}",
    "rooms_from": "{n}+",
    "rooms_label": "{value} rooms",
    "search_header": "🔍 Found: <b>{total}</b>\n📍 {district} · 💰 {price} · 🚪 {rooms}",
    "search_empty": (
        "🔍 Nothing matches these filters.\n📍 {district} · 💰 {price} · 🚪 {rooms}\n\n"
        "Try widening your search."
    ),
    "page_counter": "Page {page} of {pages}",
    "listing_rooms": "{n} rooms",
    "listing_area": "{area} m²",
    "fav_hint": "☆/★: add to or remove from favorites",
    "favorites_header": "❤️ <b>Favorites</b>: {total}",
    "favorites_empty": "❤️ No favorites yet.\n\nFind a home via “🔍 Search” and tap ☆.",
    "fav_added": "★ Added to favorites",
    "fav_removed": "☆ Removed from favorites",
    "listing_unavailable": "This listing is no longer available.",
    "message_outdated": "This message is outdated, please open the section again.",
    "profile": (
        "👤 <b>Profile</b>\n\n"
        "🌐 Language: {language}\n"
        "⭐ Subscription: {tier}{expires}\n"
        "💳 Balance: {balance} ₾\n"
        "❤️ Favorites: {favorites}\n"
        "📅 Member since {since}\n\n"
        "Choose interface language:"
    ),
    "subscription_until": " (until {date})",
    "tier_free": "Free",
    "tier_nomad": "Premium",
    "tier_family": "Family",
    "tier_realtor": "Realtor",
    "language_changed": "✅ Language updated.",
    # TASK-028: notifications
    "notify_new_listing": "🏠 <b>New apartment</b> for your search “{search}”\n\n{listing}",
    "notify_new_listing_no_search": "🏠 <b>New apartment</b> for your search\n\n{listing}",
    "notify_price_drop": "📉 <b>Price dropped</b>: {old} → <b>{new}</b>\n\n{listing}",
    "notify_details": "{price} · {rooms} rooms · {area} m²",
    "notify_open": "Open",
    # TASK-026/027: Premium subscription
    "premium_info": (
        "⭐ <b>Bina.ai Premium</b>\n\n"
        "{status}\n\n"
        "<b>Free:</b> unlimited favorites, {free_searches} saved search.\n"
        "<b>Premium:</b> up to {premium_searches} saved searches "
        "with alerts about new apartments.\n\n"
        "Price: <b>{price} ⭐</b> for {days} days. Paid with Telegram Stars."
    ),
    "premium_free": "You are on the free plan.",
    "premium_active": "✅ Premium is active until {date}.",
    "premium_buy": "Buy for {price} ⭐",
    "premium_extend": "Extend by {days} days for {price} ⭐",
    "premium_activated": "🎉 Thank you! Premium is active until {date}.",
    "premium_invoice_outdated": "This invoice is outdated. Open /premium and try again.",
    "premium_payment_problem": (
        "⚠️ Payment received, but we couldn't activate the subscription automatically. "
        "Please contact /paysupport and we'll fix it."
    ),
    "fraud_warning": "Possible scam signs: never pay before a viewing",
    "fav_limit": (
        "The free plan allows up to {limit} favorites. Remove some or get Premium: /premium"
    ),
    "paysupport": (
        "💬 <b>Payment support</b>\n\n"
        "If your subscription wasn't activated or you need a refund of Stars, reply to "
        "this message describing the problem and the payment date."
    ),
}

TEXTS: dict[str, dict[str, str]] = {"ru": _RU, "en": _EN}

# Язык интерфейса, если для языка пользователя нет перевода
_UI_FALLBACK: dict[str, str] = {"ka": "en"}

LANGUAGE_NAMES: dict[str, str] = {"ru": "Русский", "en": "English", "ka": "ქართული"}


def ui_language(language: str) -> str:
    """Язык, на котором реально показывается интерфейс."""
    if language in TEXTS:
        return language
    return _UI_FALLBACK.get(language, DEFAULT_LANGUAGE)


def t(language: str, key: str, /, **kwargs: object) -> str:
    """Возвращает текст ``key`` на языке пользователя с подстановкой ``kwargs``."""
    template = TEXTS[ui_language(language)][key]
    return template.format(**kwargs) if kwargs else template


def all_variants(key: str) -> frozenset[str]:
    """Все переводы ``key`` (для фильтров по тексту кнопок меню)."""
    return frozenset(texts[key] for texts in TEXTS.values())
