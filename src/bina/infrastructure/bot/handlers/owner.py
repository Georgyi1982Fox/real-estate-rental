"""``/mylistings``: собственник сам размещает квартиру (TASK-096).

«🏠 Мои объявления» → «✍️ Разместить квартиру» → город → район (текстом) →
помесячно/посуточно → комнаты → площадь → цена → этаж (можно пропустить) →
описание → фото (1-10) → телефон → проверка → «Опубликовать».

Объявление сразу попадает в поиск; антифрод и перевод на другие языки его
обработают, как объявления с сайтов, а владельцу сервиса (ADMIN_TELEGRAM_IDS)
приходит сообщение с кнопкой «Скрыть». Ответы хранятся в памяти бота (FSM):
после перезапуска бота размещение придётся начать заново.
"""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from html import escape
from typing import Any
from uuid import UUID

import structlog
from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.cities import CITIES, city_name
from bina.application.listing_titles import format_area
from bina.application.owner_listings import (
    MAX_ACTIVE_LISTINGS,
    MAX_PHOTOS,
    ROOM_CHOICES,
    OwnerListingDraft,
    OwnerListingError,
    clean_phone,
    parse_area,
    parse_floor,
    telegram_contact,
    valid_description,
)
from bina.application.rent_period import DAILY, MONTHLY
from bina.application.rent_reminders import format_amount, parse_amount
from bina.application.use_cases.owner_listings import OwnerListingsUseCase
from bina.infrastructure.bot.formatters import format_listing, listing_price, listing_title
from bina.infrastructure.bot.keyboards.callbacks import (
    OwnerAction,
    OwnerCallback,
)
from bina.infrastructure.bot.keyboards.menu import main_menu, with_home
from bina.infrastructure.bot.owner_alerts import notify_admins
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import all_variants, t
from bina.infrastructure.db.models import Listing, ListingStatus, User
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository
from bina.infrastructure.db.repositories.verifications import VerificationsRepository
from bina.infrastructure.storage.photos import LocalPhotoStorage

logger = structlog.get_logger(__name__)

# Кнопки нижней клавиатуры и команды — не ответ на вопрос мастера
MENU_TEXTS = frozenset().union(
    *(
        all_variants(key)
        for key in (
            "menu_search",
            "menu_smart",
            "menu_favorites",
            "menu_profile",
            "menu_home",
            "menu_daily",
            "menu_owner",
        )
    )
)
ANSWER = F.text & ~F.text.in_(MENU_TEXTS) & ~F.text.startswith("/")
MAX_TITLE = 60


# Чат → блокировка списка фото мастера (см. on_photo)
_photo_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


class OwnerStates(StatesGroup):
    district = State()
    area = State()
    price = State()
    floor = State()
    description = State()
    photos = State()
    contact = State()
    confirm = State()
    new_price = State()


def _use_case(session: AsyncSession) -> OwnerListingsUseCase:
    return OwnerListingsUseCase(OwnerListingsRepository(session), LocalPhotoStorage())


def _button(text: str, action: OwnerAction, **values: Any) -> tuple[str, OwnerCallback]:
    return text, OwnerCallback(action=action, **values)


def _markup(*buttons: tuple[str, OwnerCallback], width: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, data in buttons:
        builder.button(text=text, callback_data=data)
    builder.adjust(width)
    return builder.as_markup()


def _status(language: str, listing: Listing, pending: frozenset[UUID] = frozenset()) -> str:
    if listing.hidden_at is not None:
        status = t(language, "owner_status_hidden")
    elif listing.status == ListingStatus.ACTIVE:
        status = t(language, "owner_status_active")
    else:
        status = t(language, "owner_status_off")
    # TASK-097, TASK-098: топ и проверка собственника
    if listing.promoted_until is not None and listing.promoted_until > datetime.now(UTC):
        status += t(language, "owner_mark_promoted", date=listing.promoted_until.strftime("%d.%m"))
    if listing.is_verified:
        status += t(language, "owner_mark_verified")
    elif listing.id in pending:
        status += t(language, "owner_mark_pending")
    return status


def render_list(
    language: str, listings: list[Listing], pending: frozenset[UUID] = frozenset()
) -> str:
    if not listings:
        return t(language, "owner_list_empty", limit=MAX_ACTIVE_LISTINGS)
    lines = [
        t(
            language,
            "owner_list_item",
            n=number,
            title=escape(listing_title(listing, language)[:MAX_TITLE]),
            price=listing_price(listing, language),
            status=_status(language, listing, pending),
        )
        for number, listing in enumerate(listings, 1)
    ]
    return t(language, "owner_list", items="\n\n".join(lines))


def list_keyboard(
    language: str, listings: list[Listing], pending: frozenset[UUID] = frozenset()
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    rows: list[int] = []
    for number, listing in enumerate(listings, 1):
        active = listing.status == ListingStatus.ACTIVE
        action = OwnerAction.OFF if active else OwnerAction.ON
        key = "owner_off" if active else "owner_on"
        builder.button(
            text=t(language, key, n=number),
            callback_data=OwnerCallback(action=action, listing=listing.id),
        )
        builder.button(
            text=t(language, "owner_edit_price", n=number),
            callback_data=OwnerCallback(action=OwnerAction.PRICE, listing=listing.id),
        )
        rows.append(2)
        # «🔥 Топ» — объявлениям в поиске; «✅ Проверка» — пока не проверено и не на проверке
        extra = 0
        if active and listing.hidden_at is None:
            builder.button(
                text=t(language, "owner_promote", n=number),
                callback_data=OwnerCallback(action=OwnerAction.PROMOTE, listing=listing.id),
            )
            extra += 1
        if not listing.is_verified and listing.id not in pending:
            builder.button(
                text=t(language, "owner_verify", n=number),
                callback_data=OwnerCallback(action=OwnerAction.VERIFY, listing=listing.id),
            )
            extra += 1
        if extra:
            rows.append(extra)
    builder.button(
        text=t(language, "owner_new"), callback_data=OwnerCallback(action=OwnerAction.NEW)
    )
    builder.adjust(*rows, 1)
    return with_home(builder.as_markup(), language)


async def cmd_mylistings(
    message: Message, user: User, session: AsyncSession, state: FSMContext
) -> None:
    """/mylistings и кнопка «🏠 Мои объявления»."""
    await state.clear()
    listings = await OwnerListingsRepository(session).list_for_user(user.id)
    pending = frozenset(await VerificationsRepository(session).pending_listing_ids(user.id))
    await message.answer(
        render_list(user.language, listings, pending),
        reply_markup=list_keyboard(user.language, listings, pending),
        disable_web_page_preview=True,
    )


# ------------------------------------------------------------------ мастер размещения


async def on_new(
    callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext
) -> None:
    language = user.language
    if await OwnerListingsRepository(session).count_active(user.id) >= MAX_ACTIVE_LISTINGS:
        await callback.answer(
            t(language, "owner_error_limit", limit=MAX_ACTIVE_LISTINGS), show_alert=True
        )
        return
    await state.clear()
    buttons = [
        _button(f"🏙 {city_name(code, language)}", OwnerAction.CITY, value=code) for code in CITIES
    ]
    if isinstance(callback.message, Message):
        await callback.message.answer(
            t(language, "owner_ask_city"), reply_markup=_markup(*buttons, width=2)
        )
    await callback.answer()


async def on_city(
    callback: CallbackQuery, callback_data: OwnerCallback, user: User, state: FSMContext
) -> None:
    city = callback_data.value if callback_data.value in CITIES else None
    if city is None or not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.set_state(OwnerStates.district)
    await state.update_data(city=city)
    await callback.message.answer(
        t(user.language, "owner_ask_district", city=city_name(city, user.language))
    )
    await callback.answer()


async def on_district(message: Message, user: User, state: FSMContext) -> None:
    district = " ".join((message.text or "").split())[:60]
    if len(district) < 2:
        await message.answer(t(user.language, "owner_bad_district"))
        return
    await state.update_data(district=district)
    await state.set_state(None)
    language = user.language
    await message.answer(
        t(language, "owner_ask_period"),
        reply_markup=_markup(
            _button(t(language, "period_to_monthly"), OwnerAction.PERIOD, value=MONTHLY),
            _button(t(language, "period_to_daily"), OwnerAction.PERIOD, value=DAILY),
            width=2,
        ),
    )


async def on_period(
    callback: CallbackQuery, callback_data: OwnerCallback, user: User, state: FSMContext
) -> None:
    if callback_data.value not in (MONTHLY, DAILY) or not isinstance(callback.message, Message):
        await callback.answer()
        return
    if not await _has(state, "city", "district"):
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    await state.update_data(period=callback_data.value)
    buttons = [
        _button(rooms_label(user.language, rooms), OwnerAction.ROOMS, value=str(rooms))
        for rooms in ROOM_CHOICES
    ]
    await callback.message.answer(
        t(user.language, "owner_ask_rooms"), reply_markup=_markup(*buttons, width=5)
    )
    await callback.answer()


def rooms_label(language: str, rooms: int) -> str:
    """«1 / студия», «2», «3», «4», «5+»."""
    if rooms == ROOM_CHOICES[0]:
        return t(language, "owner_studio")
    return f"{rooms}+" if rooms == ROOM_CHOICES[-1] else str(rooms)


async def _has(state: FSMContext, *keys: str) -> bool:
    """Предыдущие ответы мастера на месте (кнопка не из старого сообщения)."""
    data = await state.get_data()
    return all(key in data for key in keys)


async def on_rooms(
    callback: CallbackQuery, callback_data: OwnerCallback, user: User, state: FSMContext
) -> None:
    value = callback_data.value or ""
    if not value.isdigit() or not isinstance(callback.message, Message):
        await callback.answer()
        return
    if not await _has(state, "city", "district", "period"):
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    await state.update_data(rooms=int(value))
    await state.set_state(OwnerStates.area)
    await callback.message.answer(t(user.language, "owner_ask_area"))
    await callback.answer()


async def on_area(message: Message, user: User, state: FSMContext) -> None:
    area = parse_area(message.text or "")
    if area is None:
        await message.answer(t(user.language, "owner_bad_area"))
        return
    await state.update_data(area=str(area))
    await state.set_state(OwnerStates.price)
    daily = (await state.get_data()).get("period") == DAILY
    await message.answer(t(user.language, "owner_ask_price_daily" if daily else "owner_ask_price"))


async def on_price(message: Message, user: User, state: FSMContext) -> None:
    parsed = parse_amount(message.text or "")
    if parsed is None:
        await message.answer(t(user.language, "owner_bad_price"))
        return
    price, currency = parsed
    await state.update_data(price=str(price), currency=currency)
    await state.set_state(OwnerStates.floor)
    await message.answer(
        t(user.language, "owner_ask_floor"),
        reply_markup=_markup(_button(t(user.language, "owner_skip"), OwnerAction.SKIP_FLOOR)),
    )


async def on_floor(message: Message, user: User, state: FSMContext) -> None:
    parsed = parse_floor(message.text or "")
    if parsed is None:
        await message.answer(t(user.language, "owner_bad_floor"))
        return
    await state.update_data(floor=parsed[0], total_floors=parsed[1])
    await _ask_description(message, user, state)


async def on_skip_floor(callback: CallbackQuery, user: User, state: FSMContext) -> None:
    if await state.get_state() != OwnerStates.floor.state:
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    if isinstance(callback.message, Message):
        await _ask_description(callback.message, user, state)
    await callback.answer()


async def _ask_description(message: Message, user: User, state: FSMContext) -> None:
    await state.set_state(OwnerStates.description)
    await message.answer(t(user.language, "owner_ask_description"))


async def on_description(message: Message, user: User, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not valid_description(text):
        await message.answer(t(user.language, "owner_bad_description"))
        return
    await state.update_data(description=text, photos=[])
    await state.set_state(OwnerStates.photos)
    await message.answer(t(user.language, "owner_ask_photos", limit=MAX_PHOTOS))


async def on_photo(message: Message, user: User, state: FSMContext) -> None:
    """Каждое фото (и из альбома) — отдельное сообщение; берём самый большой размер."""
    if not message.photo:
        return
    # Фото альбома приходят почти одновременно и обрабатываются параллельно:
    # без блокировки два обработчика перезапишут список друг друга
    async with _photo_locks[message.chat.id]:
        photos: list[str] = list((await state.get_data()).get("photos") or [])
        if len(photos) >= MAX_PHOTOS:
            await message.answer(t(user.language, "owner_photos_full", limit=MAX_PHOTOS))
            return
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)
    await message.answer(
        t(user.language, "owner_photo_added", count=len(photos), limit=MAX_PHOTOS),
        reply_markup=_markup(_button(t(user.language, "owner_done"), OwnerAction.PHOTOS_DONE)),
    )


async def on_photos_text(message: Message, user: User) -> None:
    await message.answer(t(user.language, "owner_send_photo", limit=MAX_PHOTOS))


async def on_photos_done(callback: CallbackQuery, user: User, state: FSMContext) -> None:
    message = callback.message
    if await state.get_state() != OwnerStates.photos.state or not isinstance(message, Message):
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    if not (await state.get_data()).get("photos"):
        await callback.answer(t(user.language, "owner_need_photo"), show_alert=True)
        return
    await state.set_state(OwnerStates.contact)
    username = callback.from_user.username
    await state.update_data(contact_url=telegram_contact(username))
    keyboard = [[KeyboardButton(text=t(user.language, "owner_share_phone"), request_contact=True)]]
    if telegram_contact(username):
        keyboard.append([KeyboardButton(text=t(user.language, "owner_no_phone"))])
    await message.answer(
        t(user.language, "owner_ask_phone"),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True
        ),
    )
    await callback.answer()


async def on_contact(message: Message, user: User, state: FSMContext) -> None:
    """Номер кнопкой «Отправить номер», текстом или «Без телефона» (есть имя в Telegram)."""
    data = await state.get_data()
    phone: str | None = None
    if message.contact is not None:
        phone = clean_phone(message.contact.phone_number)
    elif message.text in all_variants("owner_no_phone") and data.get("contact_url"):
        phone = None
    else:
        phone = clean_phone(message.text or "")
        if phone is None:
            await message.answer(t(user.language, "owner_bad_phone"))
            return
    await state.update_data(phone=phone)
    await state.set_state(OwnerStates.confirm)
    # Вернуть обычную клавиатуру меню вместо кнопки «Отправить номер»
    await message.answer(t(user.language, "owner_phone_ok"), reply_markup=main_menu(user.language))
    await message.answer(
        render_preview(user.language, await state.get_data()),
        reply_markup=_markup(
            _button(t(user.language, "owner_publish"), OwnerAction.PUBLISH),
            _button(t(user.language, "owner_cancel"), OwnerAction.CANCEL),
        ),
        disable_web_page_preview=True,
    )


def draft_from(data: dict[str, Any]) -> OwnerListingDraft:
    return OwnerListingDraft(
        city=str(data["city"]),
        district=str(data["district"]),
        rent_period=str(data.get("period") or MONTHLY),
        price=Decimal(str(data["price"])),
        currency=str(data.get("currency") or "GEL"),
        rooms=int(data["rooms"]),
        area=Decimal(str(data["area"])),
        description=str(data["description"]),
        floor=data.get("floor"),
        total_floors=data.get("total_floors"),
        phone=data.get("phone"),
        contact_url=data.get("contact_url"),
    )


def render_preview(language: str, data: dict[str, Any]) -> str:
    draft = draft_from(data)
    price = format_amount(draft.price, draft.currency)
    if draft.rent_period == DAILY:
        price = f"{price} {t(language, 'per_day')}"
    floor = "—"
    if draft.floor is not None:
        floor = f"{draft.floor}/{draft.total_floors}" if draft.total_floors else str(draft.floor)
    return t(
        language,
        "owner_preview",
        city=city_name(draft.city, language),
        district=escape(draft.district),
        rooms=draft.rooms,
        area=format_area(draft.area),
        price=price,
        floor=floor,
        photos=len(data.get("photos") or []),
        phone=draft.phone or "—",
        telegram=escape(draft.contact_url or "—"),
        description=escape(draft.description[:500]),
    )


async def download_photos(bot: Bot, file_ids: list[str]) -> list[bytes]:
    """Фото из Telegram (на тестах подменяется)."""
    photos: list[bytes] = []
    for file_id in file_ids:
        buffer = await bot.download(file_id)
        if buffer is not None:
            photos.append(buffer.read())
    return photos


async def on_publish(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    settings: BotSettings,
) -> None:
    message = callback.message
    if await state.get_state() != OwnerStates.confirm.state or not isinstance(message, Message):
        await callback.answer(t(user.language, "message_outdated"), show_alert=True)
        return
    await callback.answer()
    data = await state.get_data()
    photos = await download_photos(bot, list(data.get("photos") or []))
    try:
        me = await bot.me()
        listing = await _use_case(session).publish(
            user.id, draft_from(data), photos, datetime.now(UTC), bot_username=me.username
        )
    except OwnerListingError as exc:
        await message.answer(t(user.language, f"owner_error_{exc.code}", limit=MAX_ACTIVE_LISTINGS))
        return
    await session.commit()
    await state.clear()
    await message.answer(
        t(user.language, "owner_published", listing=format_listing(listing, 1, user.language)),
        reply_markup=_markup(_button(t(user.language, "owner_my"), OwnerAction.LIST)),
    )
    await notify_admins(bot, settings.admin_ids, listing, user)


async def on_cancel(callback: CallbackQuery, user: User, state: FSMContext) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.answer(t(user.language, "owner_cancelled"))
    await callback.answer()


# ------------------------------------------------------------------ свои объявления


async def on_list(
    callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext
) -> None:
    if isinstance(callback.message, Message):
        await cmd_mylistings(callback.message, user, session, state)
    await callback.answer()


async def on_toggle(
    callback: CallbackQuery,
    callback_data: OwnerCallback,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if callback_data.listing is None:
        await callback.answer()
        return
    active = callback_data.action == OwnerAction.ON
    try:
        await _use_case(session).set_active(
            user.id, callback_data.listing, active, datetime.now(UTC)
        )
    except OwnerListingError as exc:
        await callback.answer(
            t(user.language, f"owner_error_{exc.code}", limit=MAX_ACTIVE_LISTINGS),
            show_alert=True,
        )
        return
    await callback.answer(t(user.language, "owner_turned_on" if active else "owner_turned_off"))
    if isinstance(callback.message, Message):
        await cmd_mylistings(callback.message, user, session, state)


async def on_edit_price(
    callback: CallbackQuery, callback_data: OwnerCallback, user: User, state: FSMContext
) -> None:
    if callback_data.listing is None or not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.clear()
    await state.set_state(OwnerStates.new_price)
    await state.update_data(listing=str(callback_data.listing))
    await callback.message.answer(t(user.language, "owner_ask_new_price"))
    await callback.answer()


async def on_new_price(
    message: Message, user: User, session: AsyncSession, state: FSMContext
) -> None:
    parsed = parse_amount(message.text or "")
    if parsed is None:
        await message.answer(t(user.language, "owner_bad_price"))
        return
    listing_id = UUID(str((await state.get_data())["listing"]))
    await state.clear()
    try:
        listing = await _use_case(session).update_price(
            user.id, listing_id, parsed[0], parsed[1], datetime.now(UTC)
        )
    except OwnerListingError as exc:
        await message.answer(t(user.language, f"owner_error_{exc.code}", limit=MAX_ACTIVE_LISTINGS))
        return
    await message.answer(
        t(user.language, "owner_price_saved", price=listing_price(listing, user.language)),
        reply_markup=_markup(_button(t(user.language, "owner_my"), OwnerAction.LIST)),
    )


def _action(action: OwnerAction) -> Any:
    return OwnerCallback.filter(F.action == action)


def create_router() -> Router:
    router = Router(name="owner")
    router.message.register(cmd_mylistings, Command("mylistings"))
    router.message.register(cmd_mylistings, F.text.in_(all_variants("menu_owner")))
    router.message.register(on_district, StateFilter(OwnerStates.district), ANSWER)
    router.message.register(on_area, StateFilter(OwnerStates.area), ANSWER)
    router.message.register(on_price, StateFilter(OwnerStates.price), ANSWER)
    router.message.register(on_floor, StateFilter(OwnerStates.floor), ANSWER)
    router.message.register(on_description, StateFilter(OwnerStates.description), ANSWER)
    router.message.register(on_photo, StateFilter(OwnerStates.photos), F.photo)
    router.message.register(on_photos_text, StateFilter(OwnerStates.photos), ANSWER)
    router.message.register(on_contact, StateFilter(OwnerStates.contact), F.contact)
    router.message.register(on_contact, StateFilter(OwnerStates.contact), ANSWER)
    router.message.register(on_new_price, StateFilter(OwnerStates.new_price), ANSWER)
    router.callback_query.register(on_new, _action(OwnerAction.NEW))
    router.callback_query.register(on_city, _action(OwnerAction.CITY))
    router.callback_query.register(on_period, _action(OwnerAction.PERIOD))
    router.callback_query.register(on_rooms, _action(OwnerAction.ROOMS))
    router.callback_query.register(on_skip_floor, _action(OwnerAction.SKIP_FLOOR))
    router.callback_query.register(on_photos_done, _action(OwnerAction.PHOTOS_DONE))
    router.callback_query.register(on_publish, _action(OwnerAction.PUBLISH))
    router.callback_query.register(on_cancel, _action(OwnerAction.CANCEL))
    router.callback_query.register(on_list, _action(OwnerAction.LIST))
    router.callback_query.register(on_toggle, _action(OwnerAction.OFF))
    router.callback_query.register(on_toggle, _action(OwnerAction.ON))
    router.callback_query.register(on_edit_price, _action(OwnerAction.PRICE))
    return router
