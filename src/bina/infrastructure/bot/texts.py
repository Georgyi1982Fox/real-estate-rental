"""Тексты интерфейса бота.

Интерфейс переведён на русский, английский и грузинский (TASK-116).
"""

from bina.application.use_cases.register_user import DEFAULT_LANGUAGE

_RU: dict[str, str] = {
    "menu_home": "🏠 Главное меню",
    "too_fast": "⏳ Слишком много сообщений подряд. Подождите несколько секунд.",
    # TASK-043: сообщения владельцу о сбоях
    "alert_step_failed": "⚠️ Bina.ai: сломался шаг «{step}»: {error}",
    "alert_step_ok": "✅ Bina.ai: шаг «{step}» снова работает.",
    "alert_source_empty": (
        "⚠️ Bina.ai: {source} уже {runs} запуска подряд не даёт объявлений — возможно, "
        "сайт изменился или блокирует парсер."
    ),
    "alert_source_ok": "✅ Bina.ai: {source} снова даёт объявления ({count}).",
    "alert_api_down": "🔴 Bina.ai: сервер мини-приложения не отвечает ({error}).",
    "alert_api_ok": "✅ Bina.ai: сервер мини-приложения снова работает.",
    "menu_title": (
        "🏠 <b>Bina.ai — главное меню</b>\n\n"
        "Аренда жилья в Грузии, помесячно и посуточно: объявления с MyHome.ge, SS.ge, "
        "Livo.ge, Korter.ge и Telegram-каналов, проверка на мошенничество, "
        "документы и напоминания.\n\n"
        "🧠 Можно просто написать мне, какую квартиру ищете, — своими словами.\n\n"
        "Выберите, что сделать:"
    ),
    "menu_premium": "⭐ Premium",
    "menu_invite": "🎁 Пригласить друга",
    "menu_rent": "🗓 Оплата аренды",
    # TASK-096: собственник размещает квартиру
    "menu_owner": "🏠 Сдать квартиру",
    "owner_list": (
        "🏠 <b>Ваши объявления</b>\n"
        "\n"
        "{items}\n"
        "\n"
        "Объявления видны всем в поиске. Сдали квартиру — снимите объявление."
    ),
    "owner_list_empty": (
        "🏠 <b>Сдаёте квартиру?</b>\n"
        "\n"
        "Разместите объявление бесплатно: его увидят все, кто ищет жильё в Bina.ai. Это "
        "займёт пару минут: город, район, цена, фото и описание.\n"
        "\n"
        "Можно до {limit} объявлений одновременно."
    ),
    "owner_list_item": "<b>{n}. {title}</b>\n💰 {price} · {status}",
    "owner_status_active": "🟢 в поиске",
    "owner_status_off": "⚪ снято",
    "owner_status_hidden": "🔴 скрыто модератором",
    "owner_new": "✍️ Разместить квартиру",
    "owner_off": "⚪ Снять №{n}",
    "owner_on": "🟢 Вернуть №{n}",
    "owner_edit_price": "💰 Цена №{n}",
    "owner_my": "🏠 Мои объявления",
    "owner_ask_city": "🏙 <b>Шаг 1.</b> В каком городе квартира?",
    "owner_ask_district": "📍 <b>Шаг 2.</b> Напишите район ({city}), например: <i>Ваке</i>.",
    "owner_bad_district": "Напишите название района (хотя бы 2 буквы).",
    "owner_ask_period": "📅 <b>Шаг 3.</b> Как сдаёте?",
    "owner_ask_rooms": "🚪 <b>Шаг 4.</b> Сколько комнат?",
    "owner_studio": "1 / студия",
    "owner_ask_area": "📐 <b>Шаг 5.</b> Площадь в м², например: <i>60</i>.",
    "owner_bad_area": "Напишите площадь числом от 10 до 1000, например: 60.",
    "owner_ask_price": (
        "💰 <b>Шаг 6.</b> Цена в месяц, например: <i>1500</i> (лари) или <i>600$</i>."
    ),
    "owner_ask_price_daily": (
        "💰 <b>Шаг 6.</b> Цена за сутки, например: <i>100</i> (лари) или <i>40$</i>."
    ),
    "owner_bad_price": "Не понял цену. Напишите число, например: 1500 или 600$.",
    "owner_ask_floor": (
        "🏢 <b>Шаг 7.</b> Этаж и этажей в доме, например: <i>5/9</i>. Можно пропустить."
    ),
    "owner_bad_floor": "Напишите этаж так: 5/9 (или просто 5). Или нажмите «Пропустить».",
    "owner_skip": "⏭ Пропустить",
    "owner_ask_description": (
        "📝 <b>Шаг 8.</b> Опишите квартиру: ремонт, мебель и техника, что рядом, условия "
        "(залог, животные). На любом языке — переведём на грузинский, русский и английский."
    ),
    "owner_bad_description": "Описание — от 20 до 3000 знаков. Напишите чуть подробнее.",
    "owner_ask_photos": (
        "📷 <b>Шаг 9.</b> Пришлите фото квартиры (до {limit}). Можно сразу несколько."
    ),
    "owner_photo_added": "📷 Фото {count}/{limit}. Пришлите ещё или нажмите «Готово».",
    "owner_photos_full": "Уже {limit} фото — больше нельзя. Нажмите «Готово».",
    "owner_send_photo": "Пришлите фото (до {limit}) или нажмите «Готово» под последним фото.",
    "owner_need_photo": "Нужно хотя бы одно фото.",
    "owner_done": "✅ Готово",
    "owner_ask_phone": (
        "📱 <b>Шаг 10.</b> Как с вами связаться? Нажмите «Отправить номер» или напишите телефон."
    ),
    "owner_share_phone": "📱 Отправить номер",
    "owner_no_phone": "✉️ Только через Telegram",
    "owner_bad_phone": "Не похоже на телефон. Напишите номер цифрами, например: +995555123456.",
    "owner_phone_ok": "👍 Спасибо!",
    "owner_preview": (
        "👀 <b>Проверьте объявление</b>\n"
        "\n"
        "🏙 {city}, {district}\n"
        "🚪 Комнат: {rooms} · 📐 {area} м² · 🏢 Этаж: {floor}\n"
        "💰 {price}\n"
        "📷 Фото: {photos}\n"
        "📱 Телефон: {phone}\n"
        "✉️ Telegram: {telegram}\n"
        "\n"
        "{description}"
    ),
    "owner_publish": "✅ Опубликовать",
    "owner_cancel": "❌ Отменить",
    "owner_cancelled": "Размещение отменено.",
    "owner_published": (
        "🎉 <b>Объявление опубликовано!</b> Его уже видно в поиске.\n"
        "\n"
        "{listing}\n"
        "\n"
        "Сдали квартиру — снимите объявление в «🏠 Мои объявления»."
    ),
    "owner_turned_off": "Объявление снято",
    "owner_turned_on": "Объявление снова в поиске",
    "owner_ask_new_price": "💰 Напишите новую цену, например: 1400 или 550$.",
    "owner_price_saved": "✅ Новая цена: {price}",
    "owner_error_limit": (
        "Можно держать в поиске не больше {limit} объявлений. Снимите одно из старых."
    ),
    "owner_error_no_contact": (
        "Нужен телефон или имя пользователя в Telegram, чтобы с вами могли связаться."
    ),
    "owner_error_not_found": "Объявление не найдено.",
    "owner_error_too_many_photos": "Слишком много фото.",
    "owner_error_bad_photo": "Это не фото.",
    "owner_admin_new": (
        "🆕 <b>Новое объявление собственника</b>\n\n{listing}\n📷 Фото: {photos}\n\n{description}"
    ),
    "owner_admin_hide": "🚫 Скрыть",
    "menu_help": "❓ Помощь",
    "menu_support": "💬 Поддержка",
    "menu_terms": "📄 Соглашение",
    "menu_privacy": "🔒 Конфиденциальность",
    "menu_admin": "📊 Админка",
    "menu_lab": "🧪 Проверка функций",
    "welcome_new": (
        "👋 Добро пожаловать в <b>Bina.ai</b>!\n\n"
        "Я помогу найти жильё в аренду в Грузии: объявления с MyHome.ge, SS.ge, Livo.ge, "
        "Korter.ge и Telegram-каналов в одном месте, с переводом и проверкой на "
        "мошенничество.\n\n"
        "Нажмите «🔍 Поиск», чтобы начать, или /help, чтобы узнать больше."
    ),
    "welcome_back": "👋 С возвращением! Выберите действие в меню ниже.",
    "help": (
        "<b>Bina.ai: аренда жилья в Грузии</b>\n\n"
        "/search: поиск по району, цене и количеству комнат\n"
        "/smart: умный поиск своими словами\n"
        "/daily: посуточная аренда\n"
        "/favorites: избранные объявления\n"
        "/profile: профиль, подписка и язык\n"
        "/premium: Premium-подписка\n"
        "/invite: пригласить друга\n"
        "/rent: напоминания об оплате аренды\n"
        "/mylistings: сдать свою квартиру\n"
        "/terms: пользовательское соглашение\n"
        "/privacy: политика конфиденциальности\n"
        "/help: эта справка\n\n"
        "🧠 Или просто напишите, что ищете, например: «двушка с балконом у метро до 1500».\n\n"
        "Добавляйте объявления в избранное кнопками ☆ под результатами поиска."
    ),
    "unknown": "Не понял 🤔 Воспользуйтесь меню или командой /help.",
    "menu_smart": "🧠 Умный поиск",
    "menu_daily": "🛏 Посуточно",
    "daily_search_title": "🛏 <b>Посуточная аренда</b> (цена за сутки)",
    "smart_intro": (
        "🧠 <b>Умный поиск</b>\n\n"
        "Напишите мне обычным сообщением, какую квартиру ищете, — своими словами, "
        "как написали бы знакомому риелтору. Я найду объявления, подходящие по смыслу, "
        "даже если в них другие слова.\n\n"
        "Например:\n"
        "• <i>двушка с балконом у метро до 1500 лари</i>\n"
        "• <i>квартира у моря в Батуми, можно с котом</i>\n"
        "• <i>тихая квартира с ремонтом для семьи в Ваке</i>\n\n"
        "Можно писать по-русски, по-грузински или по-английски. ✍️ Жду ваше сообщение!"
    ),
    "smart_unavailable": (
        "🧠 Умный поиск сейчас недоступен. Воспользуйтесь обычным поиском: 🔍 Поиск."
    ),
    "smart_header": "🧠 <b>Умный поиск:</b> «{query}»\nСамые близкие по смыслу объявления:",
    "smart_empty": "🧠 По запросу «{query}» пока ничего не нашлось. Попробуйте описать иначе.",
    "smart_hint": "Пишите своими словами, что ищете: район, бюджет, балкон, метро, животные…",
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
    # TASK-092: посуточная аренда
    "choose_price_daily": "📍 {district}\n\n💰 <b>Шаг 2/3.</b> 🛏 Посуточно. Бюджет за сутки:",
    "period_to_daily": "🛏 Посуточно",
    "period_to_monthly": "📅 Помесячно",
    "period_daily_label": "🛏 посуточно",
    "per_day": "/ сутки",
    "choose_rooms": "📍 {district} · 💰 {price}\n\n🚪 <b>Шаг 3/3.</b> Количество комнат:",
    "any_district": "Любой район",
    "choose_city": "🏙 <b>Выберите город:</b>",
    "any_district_in": "{city}, любой район",
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
    "tier_family": "Семья",
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
        "<b>Premium:</b> до {premium_searches} сохранённых поисков, новые квартиры — "
        "сразу (бесплатно — через {free_delay} ч), уведомления «цена снижена».\n\n"
        "Цена: {prices}. Оплата звёздами Telegram."
    ),
    "premium_free": "Сейчас у вас бесплатный тариф.",
    # TASK-110: админка владельца
    "admin_stats": (
        "📊 <b>Статистика</b>\n\n"
        "👤 Пользователей: {users} (+{users_week} за неделю)\n"
        "⭐ Premium сейчас: {premium}\n"
        "💰 Звёзды: {stars_month} за 30 дней ({payments_month} оплат), всего {stars_total}\n\n"
        "🏠 Объявлений в поиске:\n{sources}\n"
        "🙈 Скрыто: {hidden} · ⚠️ открытых жалоб: {complaints}\n\n"
        "📍 Популярные районы:\n{districts}"
    ),
    "admin_refresh": "📊 Обновить",
    "admin_complaints": "⚠️ Жалобы ({count})",
    "admin_no_complaints": "Открытых жалоб нет.",
    "admin_case": "⚠️ <b>{title}</b>\n{source} · жалоб: {count}{hidden}\nПричины: {reasons}",
    "admin_case_hidden": " · уже скрыто",
    "admin_hide": "🙈 Скрыть",
    "admin_restore": "✅ Вернуть в поиск",
    "admin_hidden": "Скрыто, жалобы закрыты.",
    "admin_restored": "Возвращено в поиск, жалобы отклонены.",
    # TASK-109: напоминания об оплате аренды
    "rent_info": (
        "🗓 <b>Напоминания об оплате аренды</b>\n\n"
        "Напомню за 3 дня, за 1 день и в день оплаты. Кнопка «Оплачено» — до следующего "
        "месяца.\n\n{items}"
    ),
    "rent_empty": "Напоминаний пока нет.",
    "rent_item": "• {day}-го числа — {amount}",
    "rent_item_paid": "• {day}-го числа — {amount} (✅ оплачено за {date})",
    "rent_add": "🆕 Добавить напоминание",
    "rent_delete": "🗑 Удалить {day}-го",
    "rent_limit": "Можно не больше {limit} напоминаний.",
    "rent_choose_day": "Какого числа вы платите аренду?",
    "rent_enter_amount": (
        "Оплата {day}-го числа. Напишите сумму, например: <code>1500</code>, "
        "<code>700 $</code> или <code>650 eur</code>."
    ),
    "rent_bad_amount": (
        "Не понял сумму. Напишите число, например: <code>1500</code> или <code>700 $</code>."
    ),
    "rent_saved": "✅ Готово: напомню об оплате {amount} {day}-го числа каждого месяца.",
    "rent_deleted": "Напоминание удалено.",
    "rent_due_in": "🗓 Напоминание: {date} оплата аренды — {amount} (через {days} дн.).",
    "rent_due_today": "🔔 Сегодня день оплаты аренды: {amount}.",
    "rent_paid_button": "✅ Оплачено",
    "rent_paid_done": (
        "✅ Отмечено: аренда за {date} оплачена. Следующее напоминание — в следующем месяце."
    ),
    # TASK-108: приглашения
    "premium_discount": "🎁 По приглашению друга вам скидка {percent}% на первую покупку.",
    "welcome_referred": (
        "🎁 Вас пригласил друг: скидка {percent}% на первую покупку Premium — /premium"
    ),
    "invite_info": (
        "🎁 <b>Пригласите друзей</b>\n\n"
        "Друг получит скидку {percent}% на первый Premium, а вы — {days} дней Premium, "
        "когда он оплатит (до {limit} наград в месяц).\n\n"
        "Ваша ссылка:\n{link}\n\n"
        "Приглашено: {invited}, наград: {rewarded}."
    ),
    "premium_active": "✅ Premium действует до {date}.",
    "premium_price": "<b>{price} ⭐</b> за {days} дн.",
    "premium_buy": "Купить {days} дн. за {price} ⭐",
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
    "chat_card": (
        "🏠 <b>{title}</b>\n"
        "💰 {price}\n"
        "\n"
        "Напишите хозяину на своём языке — бот переведёт сообщение на его язык. Или запишитесь "
        "на просмотр."
    ),
    "chat_open_button": "💬 {n}",
    "chat_write_button": "✍️ Написать хозяину",
    "chat_view_button": "📅 Записаться на просмотр",
    "chat_prompt": (
        "✍️ Напишите сообщение хозяину. Бот переведёт его на язык хозяина.\n"
        "\n"
        "Передумали — нажмите «🏠 Главное меню»."
    ),
    "chat_reply_prompt": "✍️ Напишите ответ. Бот переведёт его на язык собеседника.",
    "chat_sent": "✅ Отправлено. Ответ придёт сюда, в этот чат.",
    "chat_to_owner": "💬 <b>Сообщение от арендатора</b>\n🏠 {title}\n\n{text}",
    "chat_to_tenant": "💬 <b>Ответ хозяина</b>\n🏠 {title}\n\n{text}",
    "chat_original": "Оригинал: {text}",
    "chat_reply_button": "↩️ Ответить",
    "chat_not_delivered": "Не удалось доставить: собеседник остановил бота.",
    "chat_error_not_found": "Это объявление больше недоступно.",
    "chat_error_own_listing": "Это ваше объявление 🙂",
    "chat_error_limit": (
        "Сегодня вы уже начали {n} новых диалогов. Новые можно будет начать завтра."
    ),
    "chat_error_too_long": "Слишком длинное сообщение: можно до {n} знаков.",
    "chat_error_empty": "Отправьте сообщение текстом.",
    "view_choose_day": "📅 Выберите день просмотра:",
    "view_choose_hour": "🕐 {day}: выберите время просмотра:",
    "view_no_hours": "На этот день свободного времени нет, выберите другой.",
    "view_today": "Сегодня",
    "view_tomorrow": "Завтра",
    "weekdays_short": "пн,вт,ср,чт,пт,сб,вс",
    "view_when": "{weekday} {date} в {time}",
    "view_requested": (
        "✅ Просьба отправлена хозяину: {when}. Бот сообщит, как только он ответит."
    ),
    "view_to_owner": (
        "📅 <b>Просьба о просмотре</b>\n🏠 {title}\n🕐 {when}\n\nВам подходит это время?"
    ),
    "view_confirm_button": "✅ Подходит",
    "view_decline_button": "❌ Другое время",
    "view_confirmed_owner": "✅ Просмотр подтверждён: {when}. Бот напомнит за 2 часа.",
    "view_declined_owner": "Хорошо, арендатор выберет другое время.",
    "view_confirmed_tenant": (
        "✅ <b>Хозяин подтвердил просмотр</b>\n"
        "🏠 {title}\n"
        "🕐 {when}{address}\n"
        "\n"
        "Бот напомнит за 2 часа."
    ),
    "view_declined_tenant": (
        "❌ Хозяину не подходит {when}\n🏠 {title}\n\nВыберите другое время или напишите хозяину."
    ),
    "view_reminder": "⏰ <b>Напоминание: просмотр сегодня в {time}</b>\n🏠 {title}{address}",
    "view_address": "\n📍 {address}",
    "view_error_slot_taken": "Это время уже занято, выберите другое.",
    "view_error_slot_invalid": "Это время уже недоступно, выберите другое.",
    "view_error_too_many_viewings": (
        "У вас уже {n} просьбы о просмотре без ответа. Дождитесь ответа хозяев."
    ),
    "view_error_already_answered": "Вы уже ответили на эту просьбу.",
}

_EN: dict[str, str] = {
    "menu_home": "🏠 Main menu",
    "too_fast": "⏳ Too many messages in a row. Please wait a few seconds.",
    # TASK-043: owner alerts
    "alert_step_failed": "⚠️ Bina.ai: the «{step}» step failed: {error}",
    "alert_step_ok": "✅ Bina.ai: the «{step}» step works again.",
    "alert_source_empty": (
        "⚠️ Bina.ai: {source} returned no listings {runs} runs in a row — the site may have "
        "changed or be blocking the scraper."
    ),
    "alert_source_ok": "✅ Bina.ai: {source} returns listings again ({count}).",
    "alert_api_down": "🔴 Bina.ai: the Mini App server is not responding ({error}).",
    "alert_api_ok": "✅ Bina.ai: the Mini App server works again.",
    "menu_title": (
        "🏠 <b>Bina.ai — main menu</b>\n\n"
        "Monthly and daily rentals in Georgia: listings from MyHome.ge, SS.ge, Livo.ge, "
        "Korter.ge and Telegram channels, scam checks, documents and reminders.\n\n"
        "🧠 You can also just write to me what apartment you need, in your own words.\n\n"
        "Choose what to do:"
    ),
    "menu_premium": "⭐ Premium",
    "menu_invite": "🎁 Invite a friend",
    "menu_rent": "🗓 Rent payments",
    # TASK-096: собственник размещает квартиру
    "menu_owner": "🏠 Rent out an apartment",
    "owner_list": (
        "🏠 <b>Your listings</b>\n"
        "\n"
        "{items}\n"
        "\n"
        "Everyone sees your listings in search. Rented it out? Take the listing down."
    ),
    "owner_list_empty": (
        "🏠 <b>Renting out an apartment?</b>\n"
        "\n"
        "Post a listing for free: everyone looking for a home on Bina.ai will see it. It "
        "takes a couple of minutes: city, district, price, photos and description.\n"
        "\n"
        "Up to {limit} listings at a time."
    ),
    "owner_list_item": "<b>{n}. {title}</b>\n💰 {price} · {status}",
    "owner_status_active": "🟢 in search",
    "owner_status_off": "⚪ taken down",
    "owner_status_hidden": "🔴 hidden by moderator",
    "owner_new": "✍️ Post an apartment",
    "owner_off": "⚪ Take down #{n}",
    "owner_on": "🟢 Restore #{n}",
    "owner_edit_price": "💰 Price #{n}",
    "owner_my": "🏠 My listings",
    "owner_ask_city": "🏙 <b>Step 1.</b> Which city is the apartment in?",
    "owner_ask_district": (
        "📍 <b>Step 2.</b> Type the district ({city}), for example: <i>Vake</i>."
    ),
    "owner_bad_district": "Type the district name (at least 2 letters).",
    "owner_ask_period": "📅 <b>Step 3.</b> How do you rent it out?",
    "owner_ask_rooms": "🚪 <b>Step 4.</b> How many rooms?",
    "owner_studio": "1 / studio",
    "owner_ask_area": "📐 <b>Step 5.</b> Area in m², for example: <i>60</i>.",
    "owner_bad_area": "Type the area as a number from 10 to 1000, for example: 60.",
    "owner_ask_price": (
        "💰 <b>Step 6.</b> Price per month, for example: <i>1500</i> (GEL) or <i>600$</i>."
    ),
    "owner_ask_price_daily": (
        "💰 <b>Step 6.</b> Price per day, for example: <i>100</i> (GEL) or <i>40$</i>."
    ),
    "owner_bad_price": "I didn't get the price. Type a number, for example: 1500 or 600$.",
    "owner_ask_floor": (
        "🏢 <b>Step 7.</b> Floor and floors in the building, for example: <i>5/9</i>. You "
        "can skip this."
    ),
    "owner_bad_floor": "Type the floor like this: 5/9 (or just 5). Or tap “Skip”.",
    "owner_skip": "⏭ Skip",
    "owner_ask_description": (
        "📝 <b>Step 8.</b> Describe the apartment: renovation, furniture and appliances, "
        "what's nearby, terms (deposit, pets). Any language — we'll translate it into "
        "Georgian, Russian and English."
    ),
    "owner_bad_description": (
        "The description should be 20 to 3000 characters. Please add a bit more."
    ),
    "owner_ask_photos": (
        "📷 <b>Step 9.</b> Send photos of the apartment (up to {limit}). You can send "
        "several at once."
    ),
    "owner_photo_added": "📷 Photo {count}/{limit}. Send more or tap “Done”.",
    "owner_photos_full": "That's already {limit} photos, the maximum. Tap “Done”.",
    "owner_send_photo": "Send photos (up to {limit}) or tap “Done” under the last photo.",
    "owner_need_photo": "At least one photo is needed.",
    "owner_done": "✅ Done",
    "owner_ask_phone": (
        "📱 <b>Step 10.</b> How can people contact you? Tap “Share number” or type your phone."
    ),
    "owner_share_phone": "📱 Share number",
    "owner_no_phone": "✉️ Telegram only",
    "owner_bad_phone": (
        "That doesn't look like a phone number. Type it in digits, for example: +995555123456."
    ),
    "owner_phone_ok": "👍 Thanks!",
    "owner_preview": (
        "👀 <b>Check your listing</b>\n"
        "\n"
        "🏙 {city}, {district}\n"
        "🚪 Rooms: {rooms} · 📐 {area} m² · 🏢 Floor: {floor}\n"
        "💰 {price}\n"
        "📷 Photos: {photos}\n"
        "📱 Phone: {phone}\n"
        "✉️ Telegram: {telegram}\n"
        "\n"
        "{description}"
    ),
    "owner_publish": "✅ Publish",
    "owner_cancel": "❌ Cancel",
    "owner_cancelled": "Posting cancelled.",
    "owner_published": (
        "🎉 <b>Your listing is live!</b> It already shows up in search.\n"
        "\n"
        "{listing}\n"
        "\n"
        "Rented it out? Take it down in “🏠 My listings”."
    ),
    "owner_turned_off": "Listing taken down",
    "owner_turned_on": "Listing is back in search",
    "owner_ask_new_price": "💰 Type the new price, for example: 1400 or 550$.",
    "owner_price_saved": "✅ New price: {price}",
    "owner_error_limit": (
        "You can have at most {limit} listings in search. Take down one of the old ones."
    ),
    "owner_error_no_contact": (
        "A phone number or a Telegram username is needed so people can contact you."
    ),
    "owner_error_not_found": "Listing not found.",
    "owner_error_too_many_photos": "Too many photos.",
    "owner_error_bad_photo": "That's not a photo.",
    "owner_admin_new": (
        "🆕 <b>New owner listing</b>\n\n{listing}\n📷 Photos: {photos}\n\n{description}"
    ),
    "owner_admin_hide": "🚫 Hide",
    "menu_help": "❓ Help",
    "menu_support": "💬 Support",
    "menu_terms": "📄 Terms",
    "menu_privacy": "🔒 Privacy",
    "menu_admin": "📊 Admin",
    "menu_lab": "🧪 Feature check",
    "welcome_new": (
        "👋 Welcome to <b>Bina.ai</b>!\n\n"
        "I'll help you find a rental home in Georgia: listings from MyHome.ge, SS.ge, "
        "Livo.ge, Korter.ge and Telegram channels in one place, translated and checked "
        "for fraud.\n\n"
        "Tap “🔍 Search” to start, or /help to learn more."
    ),
    "welcome_back": "👋 Welcome back! Pick an option from the menu below.",
    "help": (
        "<b>Bina.ai: rentals in Georgia</b>\n\n"
        "/search: search by district, price and rooms\n"
        "/smart: smart search in your own words\n"
        "/daily: daily rent\n"
        "/favorites: your saved listings\n"
        "/profile: profile, subscription and language\n"
        "/premium: Premium subscription\n"
        "/invite: invite a friend\n"
        "/rent: rent payment reminders\n"
        "/mylistings: rent out your apartment\n"
        "/terms: terms of use\n"
        "/privacy: privacy policy\n"
        "/help: this help\n\n"
        "🧠 Or just write what you need, e.g. "
        "«2 rooms with a balcony near the metro up to 1500».\n\n"
        "Save listings with the ☆ buttons under search results."
    ),
    "unknown": "Sorry, I didn't get that 🤔 Use the menu or /help.",
    "menu_smart": "🧠 Smart search",
    "menu_daily": "🛏 Daily rent",
    "daily_search_title": "🛏 <b>Daily rent</b> (price per day)",
    "smart_intro": (
        "🧠 <b>Smart search</b>\n\n"
        "Just send me a message describing the apartment you want, in your own words, "
        "as you would tell a friend who is a realtor. I will find listings that match "
        "by meaning, even if they use different words.\n\n"
        "For example:\n"
        "• <i>2 rooms with a balcony near the metro up to 1500 GEL</i>\n"
        "• <i>flat by the sea in Batumi, cats allowed</i>\n"
        "• <i>quiet renovated flat for a family in Vake</i>\n\n"
        "You can write in English, Russian or Georgian. ✍️ I'm waiting for your message!"
    ),
    "smart_unavailable": (
        "🧠 Smart search is unavailable right now. Please use the regular 🔍 Search."
    ),
    "smart_header": "🧠 <b>Smart search:</b> «{query}»\nThe closest listings by meaning:",
    "smart_empty": "🧠 Nothing found for «{query}» yet. Try describing it differently.",
    "smart_hint": (
        "Describe what you need in your own words: district, budget, balcony, metro, pets…"
    ),
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
    # TASK-092: daily rent
    "choose_price_daily": "📍 {district}\n\n💰 <b>Step 2/3.</b> 🛏 Daily rent. Budget per day:",
    "period_to_daily": "🛏 Daily",
    "period_to_monthly": "📅 Monthly",
    "period_daily_label": "🛏 daily",
    "per_day": "/ day",
    "choose_rooms": "📍 {district} · 💰 {price}\n\n🚪 <b>Step 3/3.</b> Number of rooms:",
    "any_district": "Any district",
    "choose_city": "🏙 <b>Choose a city:</b>",
    "any_district_in": "{city}, any district",
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
        "<b>Premium:</b> up to {premium_searches} saved searches, new apartments "
        "right away (free plan: after {free_delay} h), price drop alerts.\n\n"
        "Price: {prices}. Paid with Telegram Stars."
    ),
    "premium_free": "You are on the free plan.",
    # TASK-110: owner admin
    "admin_stats": (
        "📊 <b>Statistics</b>\n\n"
        "👤 Users: {users} (+{users_week} this week)\n"
        "⭐ Premium now: {premium}\n"
        "💰 Stars: {stars_month} in 30 days ({payments_month} payments), {stars_total} in total\n\n"
        "🏠 Listings in search:\n{sources}\n"
        "🙈 Hidden: {hidden} · ⚠️ open complaints: {complaints}\n\n"
        "📍 Popular districts:\n{districts}"
    ),
    "admin_refresh": "📊 Refresh",
    "admin_complaints": "⚠️ Complaints ({count})",
    "admin_no_complaints": "No open complaints.",
    "admin_case": "⚠️ <b>{title}</b>\n{source} · complaints: {count}{hidden}\nReasons: {reasons}",
    "admin_case_hidden": " · already hidden",
    "admin_hide": "🙈 Hide",
    "admin_restore": "✅ Back to search",
    "admin_hidden": "Hidden, complaints closed.",
    "admin_restored": "Back in search, complaints rejected.",
    # TASK-109: rent payment reminders
    "rent_info": (
        "🗓 <b>Rent payment reminders</b>\n\n"
        "I'll remind you 3 days before, 1 day before and on the payment day. The «Paid» "
        "button stops reminders until next month.\n\n{items}"
    ),
    "rent_empty": "No reminders yet.",
    "rent_item": "• on day {day} — {amount}",
    "rent_item_paid": "• on day {day} — {amount} (✅ paid for {date})",
    "rent_add": "🆕 Add a reminder",
    "rent_delete": "🗑 Delete day {day}",
    "rent_limit": "You can have up to {limit} reminders.",
    "rent_choose_day": "On which day of the month do you pay rent?",
    "rent_enter_amount": (
        "Payment on day {day}. Send the amount, for example: <code>1500</code>, "
        "<code>700 $</code> or <code>650 eur</code>."
    ),
    "rent_bad_amount": (
        "I didn't get the amount. Send a number, e.g. <code>1500</code> or <code>700 $</code>."
    ),
    "rent_saved": "✅ Done: I'll remind you to pay {amount} on day {day} of every month.",
    "rent_deleted": "Reminder deleted.",
    "rent_due_in": "🗓 Reminder: rent of {amount} is due on {date} (in {days} days).",
    "rent_due_today": "🔔 Rent is due today: {amount}.",
    "rent_paid_button": "✅ Paid",
    "rent_paid_done": "✅ Marked as paid for {date}. The next reminder will come next month.",
    # TASK-108: invitations
    "premium_discount": "🎁 You were invited by a friend: {percent}% off your first purchase.",
    "welcome_referred": (
        "🎁 A friend invited you: {percent}% off your first Premium purchase — /premium"
    ),
    "invite_info": (
        "🎁 <b>Invite friends</b>\n\n"
        "Your friend gets {percent}% off their first Premium, and you get {days} days of "
        "Premium when they pay (up to {limit} rewards a month).\n\n"
        "Your link:\n{link}\n\n"
        "Invited: {invited}, rewards: {rewarded}."
    ),
    "premium_active": "✅ Premium is active until {date}.",
    "premium_price": "<b>{price} ⭐</b> for {days} days",
    "premium_buy": "Buy {days} days for {price} ⭐",
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
    "chat_card": (
        "🏠 <b>{title}</b>\n"
        "💰 {price}\n"
        "\n"
        "Write to the landlord in your language and the bot will translate your message into "
        "theirs. Or book a viewing."
    ),
    "chat_open_button": "💬 {n}",
    "chat_write_button": "✍️ Message the landlord",
    "chat_view_button": "📅 Book a viewing",
    "chat_prompt": (
        "✍️ Write your message to the landlord. The bot will translate it into their "
        "language.\n"
        "\n"
        "Changed your mind? Press «🏠 Main menu»."
    ),
    "chat_reply_prompt": "✍️ Write your reply. The bot will translate it for the other person.",
    "chat_sent": "✅ Sent. The reply will arrive here, in this chat.",
    "chat_to_owner": "💬 <b>Message from a tenant</b>\n🏠 {title}\n\n{text}",
    "chat_to_tenant": "💬 <b>Reply from the landlord</b>\n🏠 {title}\n\n{text}",
    "chat_original": "Original: {text}",
    "chat_reply_button": "↩️ Reply",
    "chat_not_delivered": "Could not deliver: the other person has stopped the bot.",
    "chat_error_not_found": "This listing is no longer available.",
    "chat_error_own_listing": "This is your own listing 🙂",
    "chat_error_limit": (
        "You have already started {n} new conversations today. You can start new ones tomorrow."
    ),
    "chat_error_too_long": "The message is too long: up to {n} characters.",
    "chat_error_empty": "Please send your message as text.",
    "view_choose_day": "📅 Choose the day of the viewing:",
    "view_choose_hour": "🕐 {day}: choose the time of the viewing:",
    "view_no_hours": "No free time on this day, please choose another.",
    "view_today": "Today",
    "view_tomorrow": "Tomorrow",
    "weekdays_short": "Mon,Tue,Wed,Thu,Fri,Sat,Sun",
    "view_when": "{weekday} {date} at {time}",
    "view_requested": (
        "✅ Request sent to the landlord: {when}. The bot will let you know as soon as they answer."
    ),
    "view_to_owner": (
        "📅 <b>Viewing request</b>\n🏠 {title}\n🕐 {when}\n\nDoes this time suit you?"
    ),
    "view_confirm_button": "✅ Suits me",
    "view_decline_button": "❌ Another time",
    "view_confirmed_owner": (
        "✅ Viewing confirmed: {when}. The bot will remind you 2 hours before."
    ),
    "view_declined_owner": "OK, the tenant will choose another time.",
    "view_confirmed_tenant": (
        "✅ <b>The landlord confirmed the viewing</b>\n"
        "🏠 {title}\n"
        "🕐 {when}{address}\n"
        "\n"
        "The bot will remind you 2 hours before."
    ),
    "view_declined_tenant": (
        "❌ {when} does not suit the landlord\n"
        "🏠 {title}\n"
        "\n"
        "Choose another time or message the landlord."
    ),
    "view_reminder": "⏰ <b>Reminder: viewing today at {time}</b>\n🏠 {title}{address}",
    "view_address": "\n📍 {address}",
    "view_error_slot_taken": "This time is already taken, please choose another.",
    "view_error_slot_invalid": "This time is no longer available, please choose another.",
    "view_error_too_many_viewings": (
        "You already have {n} unanswered viewing requests. Please wait for the landlords to answer."
    ),
    "view_error_already_answered": "You have already answered this request.",
}

_KA: dict[str, str] = {
    "menu_home": "🏠 მთავარი მენიუ",
    "too_fast": "⏳ ზედიზედ ძალიან ბევრი შეტყობინებაა. დაელოდეთ რამდენიმე წამს.",
    # TASK-043: შეტყობინებები მფლობელს
    "alert_step_failed": "⚠️ Bina.ai: ნაბიჯი «{step}» გაფუჭდა: {error}",
    "alert_step_ok": "✅ Bina.ai: ნაბიჯი «{step}» ისევ მუშაობს.",
    "alert_source_empty": (
        "⚠️ Bina.ai: {source} უკვე {runs} გაშვებაა ზედიზედ განცხადებებს არ იძლევა — "
        "შესაძლოა, საიტი შეიცვალა ან ბლოკავს პარსერს."
    ),
    "alert_source_ok": "✅ Bina.ai: {source} ისევ იძლევა განცხადებებს ({count}).",
    "alert_api_down": "🔴 Bina.ai: მინი-აპლიკაციის სერვერი არ პასუხობს ({error}).",
    "alert_api_ok": "✅ Bina.ai: მინი-აპლიკაციის სერვერი ისევ მუშაობს.",
    "menu_title": (
        "🏠 <b>Bina.ai — მთავარი მენიუ</b>\n\n"
        "ქირავნობა საქართველოში, თვიურად და დღიურად: განცხადებები MyHome.ge-დან, "
        "SS.ge-დან, Livo.ge-დან, Korter.ge-დან და Telegram-არხებიდან, თაღლითობის "
        "შემოწმება, დოკუმენტები და შეხსენებები.\n\n"
        "🧠 შეგიძლიათ უბრალოდ მომწეროთ, როგორ ბინას ეძებთ — საკუთარი სიტყვებით.\n\n"
        "აირჩიეთ, რა გავაკეთოთ:"
    ),
    "menu_premium": "⭐ Premium",
    "menu_invite": "🎁 მეგობრის მოწვევა",
    "menu_rent": "🗓 ქირის გადახდა",
    # TASK-096: собственник размещает квартиру
    "menu_owner": "🏠 ბინის გაქირავება",
    "owner_list": (
        "🏠 <b>თქვენი განცხადებები</b>\n"
        "\n"
        "{items}\n"
        "\n"
        "განცხადებები ძებნაში ყველასთვის ჩანს. ბინა გააქირავეთ? მოხსენით განცხადება."
    ),
    "owner_list_empty": (
        "🏠 <b>ბინას აქირავებთ?</b>\n"
        "\n"
        "განათავსეთ განცხადება უფასოდ: მას ნახავს ყველა, ვინც Bina.ai-ზე საცხოვრებელს "
        "ეძებს. ამას რამდენიმე წუთი სჭირდება: ქალაქი, უბანი, ფასი, ფოტოები და აღწერა.\n"
        "\n"
        "ერთდროულად შეიძლება {limit} განცხადებამდე."
    ),
    "owner_list_item": "<b>{n}. {title}</b>\n💰 {price} · {status}",
    "owner_status_active": "🟢 ძებნაშია",
    "owner_status_off": "⚪ მოხსნილია",
    "owner_status_hidden": "🔴 დამალულია მოდერატორის მიერ",
    "owner_new": "✍️ ბინის განთავსება",
    "owner_off": "⚪ მოხსნა №{n}",
    "owner_on": "🟢 დაბრუნება №{n}",
    "owner_edit_price": "💰 ფასი №{n}",
    "owner_my": "🏠 ჩემი განცხადებები",
    "owner_ask_city": "🏙 <b>ნაბიჯი 1.</b> რომელ ქალაქშია ბინა?",
    "owner_ask_district": "📍 <b>ნაბიჯი 2.</b> დაწერეთ უბანი ({city}), მაგალითად: <i>ვაკე</i>.",
    "owner_bad_district": "დაწერეთ უბნის სახელი (მინიმუმ 2 ასო).",
    "owner_ask_period": "📅 <b>ნაბიჯი 3.</b> როგორ აქირავებთ?",
    "owner_ask_rooms": "🚪 <b>ნაბიჯი 4.</b> რამდენი ოთახია?",
    "owner_studio": "1 / სტუდიო",
    "owner_ask_area": "📐 <b>ნაბიჯი 5.</b> ფართი მ²-ში, მაგალითად: <i>60</i>.",
    "owner_bad_area": "დაწერეთ ფართი რიცხვით 10-დან 1000-მდე, მაგალითად: 60.",
    "owner_ask_price": (
        "💰 <b>ნაბიჯი 6.</b> ფასი თვეში, მაგალითად: <i>1500</i> (ლარი) ან <i>600$</i>."
    ),
    "owner_ask_price_daily": (
        "💰 <b>ნაბიჯი 6.</b> ფასი დღეში, მაგალითად: <i>100</i> (ლარი) ან <i>40$</i>."
    ),
    "owner_bad_price": "ფასი ვერ გავიგე. დაწერეთ რიცხვი, მაგალითად: 1500 ან 600$.",
    "owner_ask_floor": (
        "🏢 <b>ნაბიჯი 7.</b> სართული და სართულიანობა, მაგალითად: <i>5/9</i>. შეგიძლიათ გამოტოვოთ."
    ),
    "owner_bad_floor": "დაწერეთ სართული ასე: 5/9 (ან უბრალოდ 5). ან დააჭირეთ „გამოტოვება“.",
    "owner_skip": "⏭ გამოტოვება",
    "owner_ask_description": (
        "📝 <b>ნაბიჯი 8.</b> აღწერეთ ბინა: რემონტი, ავეჯი და ტექნიკა, რა არის ახლოს, "
        "პირობები (დეპოზიტი, ცხოველები). ნებისმიერ ენაზე — ვთარგმნით ქართულად, რუსულად და "
        "ინგლისურად."
    ),
    "owner_bad_description": ("აღწერა უნდა იყოს 20-დან 3000 სიმბოლომდე. დაწერეთ ცოტა დაწვრილებით."),
    "owner_ask_photos": (
        "📷 <b>ნაბიჯი 9.</b> გამოგზავნეთ ბინის ფოტოები ({limit}-მდე). შეიძლება ერთად რამდენიმე."
    ),
    "owner_photo_added": "📷 ფოტო {count}/{limit}. გამოგზავნეთ კიდევ ან დააჭირეთ „მზადაა“.",
    "owner_photos_full": "უკვე {limit} ფოტოა — მეტი არ შეიძლება. დააჭირეთ „მზადაა“.",
    "owner_send_photo": ("გამოგზავნეთ ფოტოები ({limit}-მდე) ან დააჭირეთ „მზადაა“ ბოლო ფოტოს ქვეშ."),
    "owner_need_photo": "საჭიროა მინიმუმ ერთი ფოტო.",
    "owner_done": "✅ მზადაა",
    "owner_ask_phone": (
        "📱 <b>ნაბიჯი 10.</b> როგორ დაგიკავშირდნენ? დააჭირეთ „ნომრის გაგზავნა“ ან დაწერეთ ტელეფონი."
    ),
    "owner_share_phone": "📱 ნომრის გაგზავნა",
    "owner_no_phone": "✉️ მხოლოდ Telegram-ით",
    "owner_bad_phone": "ტელეფონს არ ჰგავს. დაწერეთ ნომერი ციფრებით, მაგალითად: +995555123456.",
    "owner_phone_ok": "👍 გმადლობთ!",
    "owner_preview": (
        "👀 <b>შეამოწმეთ განცხადება</b>\n"
        "\n"
        "🏙 {city}, {district}\n"
        "🚪 ოთახები: {rooms} · 📐 {area} მ² · 🏢 სართული: {floor}\n"
        "💰 {price}\n"
        "📷 ფოტო: {photos}\n"
        "📱 ტელეფონი: {phone}\n"
        "✉️ Telegram: {telegram}\n"
        "\n"
        "{description}"
    ),
    "owner_publish": "✅ გამოქვეყნება",
    "owner_cancel": "❌ გაუქმება",
    "owner_cancelled": "განთავსება გაუქმდა.",
    "owner_published": (
        "🎉 <b>განცხადება გამოქვეყნდა!</b> ის უკვე ჩანს ძებნაში.\n"
        "\n"
        "{listing}\n"
        "\n"
        "ბინა გააქირავეთ? მოხსენით განცხადება „🏠 ჩემი განცხადებები“-ში."
    ),
    "owner_turned_off": "განცხადება მოიხსნა",
    "owner_turned_on": "განცხადება ისევ ძებნაშია",
    "owner_ask_new_price": "💰 დაწერეთ ახალი ფასი, მაგალითად: 1400 ან 550$.",
    "owner_price_saved": "✅ ახალი ფასი: {price}",
    "owner_error_limit": (
        "ძებნაში შეიძლება იყოს არაუმეტეს {limit} განცხადება. მოხსენით ერთ-ერთი ძველი."
    ),
    "owner_error_no_contact": (
        "საჭიროა ტელეფონი ან Telegram-ის მომხმარებლის სახელი, რომ დაგიკავშირდნენ."
    ),
    "owner_error_not_found": "განცხადება ვერ მოიძებნა.",
    "owner_error_too_many_photos": "ძალიან ბევრი ფოტოა.",
    "owner_error_bad_photo": "ეს ფოტო არ არის.",
    "owner_admin_new": (
        "🆕 <b>მესაკუთრის ახალი განცხადება</b>\n\n{listing}\n📷 ფოტო: {photos}\n\n{description}"
    ),
    "owner_admin_hide": "🚫 დამალვა",
    "menu_help": "❓ დახმარება",
    "menu_support": "💬 მხარდაჭერა",
    "menu_terms": "📄 შეთანხმება",
    "menu_privacy": "🔒 კონფიდენციალურობა",
    "menu_admin": "📊 ადმინისტრირება",
    "menu_lab": "🧪 ფუნქციების შემოწმება",
    "welcome_new": (
        "👋 კეთილი იყოს თქვენი მობრძანება <b>Bina.ai</b>-ში!\n\n"
        "დაგეხმარებით საქართველოში ქირით საცხოვრებლის პოვნაში: განცხადებები MyHome.ge-დან, "
        "SS.ge-დან, Livo.ge-დან, Korter.ge-დან და Telegram-არხებიდან ერთ ადგილას, "
        "თარგმანით და თაღლითობაზე შემოწმებით.\n\n"
        "დააჭირეთ „🔍 ძებნა“, რომ დაიწყოთ, ან /help დამატებითი ინფორმაციისთვის."
    ),
    "welcome_back": "👋 კეთილი იყოს თქვენი დაბრუნება! აირჩიეთ მოქმედება ქვემოთ მენიუში.",
    "help": (
        "<b>Bina.ai: ქირავნობა საქართველოში</b>\n\n"
        "/search: ძებნა უბნის, ფასისა და ოთახების მიხედვით\n"
        "/smart: ჭკვიანი ძებნა საკუთარი სიტყვებით\n"
        "/daily: დღიური ქირა\n"
        "/favorites: რჩეული განცხადებები\n"
        "/profile: პროფილი, გამოწერა და ენა\n"
        "/premium: Premium გამოწერა\n"
        "/invite: მეგობრის მოწვევა\n"
        "/rent: ქირის გადახდის შეხსენებები\n"
        "/mylistings: თქვენი ბინის გაქირავება\n"
        "/terms: სამომხმარებლო შეთანხმება\n"
        "/privacy: კონფიდენციალურობის პოლიტიკა\n"
        "/help: ეს დახმარება\n\n"
        "🧠 ან უბრალოდ დაწერეთ, რას ეძებთ, მაგ.: «ოროთახიანი აივნით მეტროსთან 1500-მდე».\n\n"
        "შეინახეთ განცხადებები ☆ ღილაკებით ძებნის შედეგების ქვეშ."
    ),
    "unknown": "ვერ გავიგე 🤔 გამოიყენეთ მენიუ ან /help.",
    "menu_smart": "🧠 ჭკვიანი ძებნა",
    "menu_daily": "🛏 დღიურად",
    "daily_search_title": "🛏 <b>დღიური ქირა</b> (ფასი დღეში)",
    "smart_intro": (
        "🧠 <b>ჭკვიანი ძებნა</b>\n\n"
        "უბრალოდ მომწერეთ ჩვეულებრივი შეტყობინებით, როგორ ბინას ეძებთ — საკუთარი "
        "სიტყვებით, როგორც ნაცნობ რიელტორს მისწერდით. ვიპოვი აზრით შესაფერის "
        "განცხადებებს, თუნდაც მათში სხვა სიტყვები იყოს.\n\n"
        "მაგალითად:\n"
        "• <i>ოროთახიანი აივნით მეტროსთან 1500 ლარამდე</i>\n"
        "• <i>ბინა ზღვასთან ბათუმში, კატით შეიძლება</i>\n"
        "• <i>მშვიდი გარემონტებული ბინა ოჯახისთვის ვაკეში</i>\n\n"
        "შეგიძლიათ დაწეროთ ქართულად, რუსულად ან ინგლისურად. ✍️ ველოდები თქვენს შეტყობინებას!"
    ),
    "smart_unavailable": ("🧠 ჭკვიანი ძებნა ახლა მიუწვდომელია. გამოიყენეთ ჩვეულებრივი 🔍 ძებნა."),
    "smart_header": "🧠 <b>ჭკვიანი ძებნა:</b> «{query}»\nაზრით ყველაზე ახლო განცხადებები:",
    "smart_empty": "🧠 მოთხოვნით «{query}» ჯერ არაფერი მოიძებნა. სცადეთ სხვანაირად აღწერა.",
    "smart_hint": (
        "დაწერეთ საკუთარი სიტყვებით, რას ეძებთ: უბანი, ბიუჯეტი, აივანი, მეტრო, ცხოველები…"
    ),
    "error": "⚠️ რაღაც შეცდომა მოხდა. სცადეთ ცოტა მოგვიანებით.",
    "menu_search": "🔍 ძებნა",
    "menu_favorites": "❤️ რჩეულები",
    "menu_profile": "👤 პროფილი",
    "open_app": "📱 Bina.ai-ს გახსნა",
    "back": "⬅️ უკან",
    "new_search": "🔄 ახალი ძებნა",
    "choose_district": "📍 <b>ნაბიჯი 1/3.</b> აირჩიეთ უბანი:",
    "no_districts": "უბნები ჯერ არ არის ჩატვირთული. ვაჩვენებ ყველა განცხადებას.",
    "choose_price": "📍 {district}\n\n💰 <b>ნაბიჯი 2/3.</b> თვიური ბიუჯეტი:",
    # TASK-092: დღიური ქირა
    "choose_price_daily": ("📍 {district}\n\n💰 <b>ნაბიჯი 2/3.</b> 🛏 დღიურად. ბიუჯეტი დღეში:"),
    "period_to_daily": "🛏 დღიურად",
    "period_to_monthly": "📅 თვიურად",
    "period_daily_label": "🛏 დღიურად",
    "per_day": "/ დღე",
    "choose_rooms": "📍 {district} · 💰 {price}\n\n🚪 <b>ნაბიჯი 3/3.</b> ოთახების რაოდენობა:",
    "any_district": "ნებისმიერი უბანი",
    "choose_city": "🏙 <b>აირჩიეთ ქალაქი:</b>",
    "any_district_in": "{city}, ნებისმიერი უბანი",
    "any_price": "ნებისმიერი ფასი",
    "any_rooms": "ნებისმიერი",
    "price_up_to": "{max} ₾-მდე",
    "price_between": "{min}–{max} ₾",  # noqa: RUF001 (en dash в диапазоне)
    "price_from": "{min} ₾-დან",
    "rooms_exact": "{n}",
    "rooms_from": "{n}+",
    "rooms_label": "{value} ოთახი",
    "search_header": "🔍 მოიძებნა: <b>{total}</b>\n📍 {district} · 💰 {price} · 🚪 {rooms}",
    "search_empty": (
        "🔍 ამ ფილტრებით ვერაფერი მოიძებნა.\n📍 {district} · 💰 {price} · 🚪 {rooms}\n\n"
        "სცადეთ ძებნის გაფართოება."
    ),
    "page_counter": "გვერდი {page} / {pages}",
    "listing_rooms": "{n} ოთახი",
    "listing_area": "{area} მ²",
    "fav_hint": "☆/★: რჩეულებში დამატება ან წაშლა",
    "favorites_header": "❤️ <b>რჩეულები</b>: {total}",
    "favorites_empty": "❤️ რჩეულები ჯერ არ გაქვთ.\n\nიპოვეთ ბინა „🔍 ძებნით“ და დააჭირეთ ☆.",
    "fav_added": "★ დაემატა რჩეულებში",
    "fav_removed": "☆ წაიშალა რჩეულებიდან",
    "listing_unavailable": "ეს განცხადება აღარ არის ხელმისაწვდომი.",
    "message_outdated": "ეს შეტყობინება მოძველებულია, გახსენით განყოფილება ხელახლა.",
    "profile": (
        "👤 <b>პროფილი</b>\n\n"
        "🌐 ენა: {language}\n"
        "⭐ გამოწერა: {tier}{expires}\n"
        "💳 ბალანსი: {balance} ₾\n"
        "❤️ რჩეულები: {favorites}\n"
        "📅 წევრი {since}-დან\n\n"
        "აირჩიეთ ინტერფეისის ენა:"
    ),
    "subscription_until": " ({date}-მდე)",
    "tier_free": "უფასო",
    "tier_nomad": "Premium",
    "tier_family": "ოჯახი",
    "tier_realtor": "რიელტორი",
    "language_changed": "✅ ენა შეიცვალა.",
    # TASK-028: შეტყობინებები
    "notify_new_listing": "🏠 <b>ახალი ბინა</b> თქვენი ძებნით „{search}“\n\n{listing}",
    "notify_new_listing_no_search": "🏠 <b>ახალი ბინა</b> თქვენი ძებნით\n\n{listing}",
    "notify_price_drop": "📉 <b>ფასი შემცირდა</b>: {old} → <b>{new}</b>\n\n{listing}",
    "notify_details": "{price} · {rooms} ოთახი · {area} მ²",
    "notify_open": "გახსნა",
    # TASK-026/027: Premium
    "premium_info": (
        "⭐ <b>Bina.ai Premium</b>\n\n"
        "{status}\n\n"
        "<b>უფასოდ:</b> შეუზღუდავი რჩეულები, {free_searches} შენახული ძებნა.\n"
        "<b>Premium:</b> {premium_searches}-მდე შენახული ძებნა, ახალი ბინები მაშინვე "
        "(უფასოდ — {free_delay} სთ-ის შემდეგ), შეტყობინებები ფასის შემცირებაზე.\n\n"
        "ფასი: {prices}. გადახდა Telegram-ის ვარსკვლავებით."
    ),
    "premium_free": "ახლა გაქვთ უფასო ტარიფი.",
    # TASK-110: ადმინისტრირება
    "admin_stats": (
        "📊 <b>სტატისტიკა</b>\n\n"
        "👤 მომხმარებლები: {users} (+{users_week} ამ კვირაში)\n"
        "⭐ Premium ახლა: {premium}\n"
        "💰 ვარსკვლავები: {stars_month} 30 დღეში ({payments_month} გადახდა), "
        "სულ {stars_total}\n\n"
        "🏠 განცხადებები ძებნაში:\n{sources}\n"
        "🙈 დამალული: {hidden} · ⚠️ ღია საჩივრები: {complaints}\n\n"
        "📍 პოპულარული უბნები:\n{districts}"
    ),
    "admin_refresh": "📊 განახლება",
    "admin_complaints": "⚠️ საჩივრები ({count})",
    "admin_no_complaints": "ღია საჩივრები არ არის.",
    "admin_case": "⚠️ <b>{title}</b>\n{source} · საჩივრები: {count}{hidden}\nმიზეზები: {reasons}",
    "admin_case_hidden": " · უკვე დამალულია",
    "admin_hide": "🙈 დამალვა",
    "admin_restore": "✅ ძებნაში დაბრუნება",
    "admin_hidden": "დამალულია, საჩივრები დახურულია.",
    "admin_restored": "დაბრუნდა ძებნაში, საჩივრები უარყოფილია.",
    # TASK-109: ქირის გადახდის შეხსენებები
    "rent_info": (
        "🗓 <b>ქირის გადახდის შეხსენებები</b>\n\n"
        "შეგახსენებთ 3 დღით ადრე, 1 დღით ადრე და გადახდის დღეს. ღილაკი „გადახდილია“ "
        "აჩერებს შეხსენებებს მომდევნო თვემდე.\n\n{items}"
    ),
    "rent_empty": "შეხსენებები ჯერ არ არის.",
    "rent_item": "• ყოველი თვის {day} რიცხვში — {amount}",
    "rent_item_paid": "• ყოველი თვის {day} რიცხვში — {amount} (✅ გადახდილია: {date})",
    "rent_add": "🆕 შეხსენების დამატება",
    "rent_delete": "🗑 {day} რიცხვის წაშლა",
    "rent_limit": "შესაძლებელია არაუმეტეს {limit} შეხსენებისა.",
    "rent_choose_day": "თვის რომელ რიცხვში იხდით ქირას?",
    "rent_enter_amount": (
        "გადახდა {day} რიცხვში. დაწერეთ თანხა, მაგალითად: <code>1500</code>, "
        "<code>700 $</code> ან <code>650 eur</code>."
    ),
    "rent_bad_amount": (
        "თანხა ვერ გავიგე. დაწერეთ რიცხვი, მაგალითად: <code>1500</code> ან <code>700 $</code>."
    ),
    "rent_saved": "✅ მზადაა: შეგახსენებთ {amount}-ის გადახდას ყოველი თვის {day} რიცხვში.",
    "rent_deleted": "შეხსენება წაიშალა.",
    "rent_due_in": "🗓 შეხსენება: ქირის გადახდა — {amount}, {date} ({days} დღეში).",
    "rent_due_today": "🔔 დღეს ქირის გადახდის დღეა: {amount}.",
    "rent_paid_button": "✅ გადახდილია",
    "rent_paid_done": (
        "✅ მონიშნულია: {date}-ის ქირა გადახდილია. შემდეგი შეხსენება — მომდევნო თვეში."
    ),
    # TASK-108: მოწვევები
    "premium_discount": "🎁 მეგობრის მოწვევით: {percent}% ფასდაკლება პირველ შეძენაზე.",
    "welcome_referred": (
        "🎁 მეგობარმა მოგიწვიათ: {percent}% ფასდაკლება პირველ Premium-ზე — /premium"
    ),
    "invite_info": (
        "🎁 <b>მოიწვიეთ მეგობრები</b>\n\n"
        "მეგობარი მიიღებს {percent}% ფასდაკლებას პირველ Premium-ზე, თქვენ კი — {days} დღე "
        "Premium-ს, როცა ის გადაიხდის (თვეში არაუმეტეს {limit} ჯილდოსი).\n\n"
        "თქვენი ბმული:\n{link}\n\n"
        "მოწვეულია: {invited}, ჯილდოები: {rewarded}."
    ),
    "premium_active": "✅ Premium მოქმედებს {date}-მდე.",
    "premium_price": "<b>{price} ⭐</b> {days} დღით",
    "premium_buy": "ყიდვა: {days} დღე — {price} ⭐",
    "premium_extend": "გაგრძელება {days} დღით — {price} ⭐",
    "premium_activated": "🎉 გმადლობთ! Premium მოქმედებს {date}-მდე.",
    "premium_invoice_outdated": "ანგარიში მოძველებულია. გახსენით /premium და სცადეთ ხელახლა.",
    "premium_payment_problem": (
        "⚠️ გადახდა მიღებულია, მაგრამ გამოწერა ავტომატურად ვერ ჩაირთო. "
        "მოგვწერეთ /paysupport-ში და გამოვასწორებთ."
    ),
    "fraud_warning": "თაღლითობის ნიშნები: ნუ გადაიხდით ნახვამდე",
    "fav_limit": (
        "უფასო ტარიფში რჩეულებში {limit} ბინამდეა შესაძლებელი. "
        "წაშალეთ ზედმეტი ან ჩართეთ Premium: /premium"
    ),
    "paysupport": (
        "💬 <b>გადახდასთან დაკავშირებული კითხვები</b>\n\n"
        "თუ გამოწერა არ ჩაირთო ან ვარსკვლავების დაბრუნება გჭირდებათ, უპასუხეთ ამ "
        "შეტყობინებას: აღწერეთ პრობლემა და გადახდის თარიღი."
    ),
    "chat_card": (
        "🏠 <b>{title}</b>\n"
        "💰 {price}\n"
        "\n"
        "მისწერეთ მეპატრონეს თქვენს ენაზე — ბოტი შეტყობინებას მის ენაზე თარგმნის. ან ჩაეწერეთ "
        "ბინის სანახავად."
    ),
    "chat_open_button": "💬 {n}",
    "chat_write_button": "✍️ მეპატრონისთვის მიწერა",
    "chat_view_button": "📅 ნახვაზე ჩაწერა",
    "chat_prompt": (
        "✍️ დაწერეთ შეტყობინება მეპატრონისთვის. ბოტი მას მეპატრონის ენაზე თარგმნის.\n"
        "\n"
        "გადაიფიქრეთ? დააჭირეთ «🏠 მთავარი მენიუ»."
    ),
    "chat_reply_prompt": "✍️ დაწერეთ პასუხი. ბოტი მას თანამოსაუბრის ენაზე თარგმნის.",
    "chat_sent": "✅ გაიგზავნა. პასუხი აქ, ამ ჩატში მოვა.",
    "chat_to_owner": "💬 <b>შეტყობინება დამქირავებლისგან</b>\n🏠 {title}\n\n{text}",
    "chat_to_tenant": "💬 <b>მეპატრონის პასუხი</b>\n🏠 {title}\n\n{text}",
    "chat_original": "ორიგინალი: {text}",
    "chat_reply_button": "↩️ პასუხი",
    "chat_not_delivered": "ვერ მიეწოდა: თანამოსაუბრემ ბოტი გააჩერა.",
    "chat_error_not_found": "ეს განცხადება აღარ არის ხელმისაწვდომი.",
    "chat_error_own_listing": "ეს თქვენი განცხადებაა 🙂",
    "chat_error_limit": "დღეს უკვე დაიწყეთ {n} ახალი საუბარი. ახლის დაწყება ხვალ შეგეძლებათ.",
    "chat_error_too_long": "შეტყობინება ძალიან გრძელია: მაქსიმუმ {n} სიმბოლო.",
    "chat_error_empty": "გთხოვთ, გამოგზავნეთ შეტყობინება ტექსტით.",
    "view_choose_day": "📅 აირჩიეთ ნახვის დღე:",
    "view_choose_hour": "🕐 {day}: აირჩიეთ ნახვის დრო:",
    "view_no_hours": "ამ დღეს თავისუფალი დრო არ არის, აირჩიეთ სხვა.",
    "view_today": "დღეს",
    "view_tomorrow": "ხვალ",
    "weekdays_short": "ორშ,სამ,ოთხ,ხუთ,პარ,შაბ,კვ",
    "view_when": "{weekday} {date}, {time}",
    "view_requested": (
        "✅ თხოვნა მეპატრონეს გაეგზავნა: {when}. ბოტი შეგატყობინებთ, როგორც კი უპასუხებს."
    ),
    "view_to_owner": "📅 <b>ნახვის თხოვნა</b>\n🏠 {title}\n🕐 {when}\n\nმოსახერხებელია ეს დრო?",
    "view_confirm_button": "✅ მაწყობს",
    "view_decline_button": "❌ სხვა დრო",
    "view_confirmed_owner": "✅ ნახვა დადასტურდა: {when}. ბოტი 2 საათით ადრე შეგახსენებთ.",
    "view_declined_owner": "კარგი, დამქირავებელი სხვა დროს აირჩევს.",
    "view_confirmed_tenant": (
        "✅ <b>მეპატრონემ ნახვა დაადასტურა</b>\n"
        "🏠 {title}\n"
        "🕐 {when}{address}\n"
        "\n"
        "ბოტი 2 საათით ადრე შეგახსენებთ."
    ),
    "view_declined_tenant": (
        "❌ მეპატრონეს არ აწყობს {when}\n🏠 {title}\n\nაირჩიეთ სხვა დრო ან მისწერეთ მეპატრონეს."
    ),
    "view_reminder": "⏰ <b>შეხსენება: ნახვა დღეს, {time}</b>\n🏠 {title}{address}",
    "view_address": "\n📍 {address}",
    "view_error_slot_taken": "ეს დრო უკვე დაკავებულია, აირჩიეთ სხვა.",
    "view_error_slot_invalid": "ეს დრო აღარ არის ხელმისაწვდომი, აირჩიეთ სხვა.",
    "view_error_too_many_viewings": (
        "უკვე გაქვთ {n} უპასუხო თხოვნა ნახვაზე. დაელოდეთ მეპატრონეების პასუხს."
    ),
    "view_error_already_answered": "ამ თხოვნას უკვე უპასუხეთ.",
}

TEXTS: dict[str, dict[str, str]] = {"ru": _RU, "en": _EN, "ka": _KA}

# Язык интерфейса, если для языка пользователя нет перевода
_UI_FALLBACK: dict[str, str] = {}

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
