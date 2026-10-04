"""Карточка квартиры по ссылке «Поделиться» (TASK-073) и подборка «Вам может понравиться»
(TASK-076).

``/start l_<id>`` — карточка с фото, ценой и кнопками: в избранное, подробнее в приложении,
на сайте, поделиться дальше. Квартира хозяина (не своя) — сразу карточка с «Написать» и
«Просмотр» (TASK-111).
"""

from html import escape
from uuid import UUID

import structlog
from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.owner_listings import OWNER_SOURCE
from bina.application.sharing import share_link, telegram_share_url
from bina.application.use_cases.recommendations import RecommendUseCase
from bina.infrastructure.bot.formatters import (
    district_name,
    format_listings,
    format_number,
    listing_price,
    listing_title,
)
from bina.infrastructure.bot.handlers import chat
from bina.infrastructure.bot.keyboards.callbacks import FavoriteToggleCallback, RecommendCallback
from bina.infrastructure.bot.keyboards.listings import FAV_OFF, FAV_ON, favorite_buttons
from bina.infrastructure.bot.keyboards.menu import with_home
from bina.infrastructure.bot.settings import BotSettings
from bina.infrastructure.bot.texts import t
from bina.infrastructure.db.models import Listing, ListingStatus, User
from bina.infrastructure.db.repositories.districts import DistrictsRepository
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository

logger = structlog.get_logger(__name__)


def _visible(listing: Listing | None) -> bool:
    return (
        listing is not None
        and not listing.is_deleted
        and listing.status == ListingStatus.ACTIVE
        and listing.hidden_at is None
    )


def photo_url(listing: Listing, mini_app_url: str | None) -> str | None:
    """Первое фото по полной ссылке (фото хозяев лежат у нас: /api/media/…)."""
    for image in listing.images or []:
        if image.startswith(("http://", "https://")):
            return image
        if image.startswith("/") and mini_app_url:
            return mini_app_url.rstrip("/") + image
    return None


def share_text(listing: Listing, language: str) -> str:
    return f"{listing_title(listing, language)} · {listing_price(listing, language)}"


def card_keyboard(
    listing: Listing,
    language: str,
    is_favorite: bool,
    bot_username: str | None,
    mini_app_url: str | None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"{FAV_ON if is_favorite else FAV_OFF} {t(language, 'card_favorite')}",
        callback_data=FavoriteToggleCallback(listing_id=listing.id),
    )
    if mini_app_url:
        url = f"{mini_app_url.rstrip('/')}/listing/{listing.id}"
        builder.row(
            InlineKeyboardButton(text=t(language, "card_open_app"), web_app=WebAppInfo(url=url))
        )
    if listing.url and listing.source_name != OWNER_SOURCE:
        builder.row(InlineKeyboardButton(text=t(language, "card_open_site"), url=listing.url))
    if bot_username:
        link = share_link(bot_username, listing.id)
        builder.row(
            InlineKeyboardButton(
                text=t(language, "share_button"),
                url=telegram_share_url(link, share_text(listing, language)),
            )
        )
    return with_home(builder.as_markup(), language)


async def show_card(
    message: Message,
    user: User,
    session: AsyncSession,
    settings: BotSettings,
    bot: Bot,
    listing_id: UUID,
) -> None:
    """Карточка квартиры по ссылке «Поделиться»."""
    listing = await ListingsRepository(session).get_by_id(listing_id)
    if listing is None or not _visible(listing):
        await message.answer(t(user.language, "listing_unavailable"))
        return
    if listing.source_name == OWNER_SOURCE and listing.owner_user_id not in (None, user.id):
        await chat.show_listing(message, user, session, listing.id)
        return
    language = user.language
    district = await DistrictsRepository(session).get_by_id(listing.district_id)
    text = t(
        language,
        "shared_card",
        title=escape(listing_title(listing, language)),
        price=listing_price(listing, language),
        rooms=t(language, "listing_rooms", n=listing.rooms),
        area=t(language, "listing_area", area=format_number(listing.area)),
        district=escape(district_name(district, language)) if district else "—",
    )
    is_favorite = await FavoritesRepository(session).exists(user.id, listing.id)
    username = (await bot.me()).username
    markup = card_keyboard(listing, language, is_favorite, username, settings.mini_app_url)
    if photo := photo_url(listing, settings.mini_app_url):
        try:
            await message.answer_photo(photo, caption=text, reply_markup=markup)
            return
        except TelegramBadRequest as exc:
            logger.info("Listing photo not sent", error=str(exc))
    await message.answer(text, reply_markup=markup)


# --- «Вам может понравиться»


async def on_recommend(
    callback: CallbackQuery, user: User, session: AsyncSession, settings: BotSettings
) -> None:
    language = user.language
    items, based_on = await RecommendUseCase(
        FavoritesRepository(session), ListingsRepository(session), DistrictsRepository(session)
    ).execute(user.id, limit=settings.page_size)
    await callback.answer()
    message = callback.message
    if message is None:
        return
    if not based_on or not items:
        # Отдельным сообщением: список избранного выше остаётся на месте
        await message.answer(t(language, "rec_need_favorites" if not based_on else "rec_none"))
        return
    text = "\n\n".join(
        [
            t(language, "rec_header"),
            format_listings(items, 1, language),
            f"<i>{t(language, 'fav_hint')}</i>",
        ]
    )
    markup = InlineKeyboardMarkup(inline_keyboard=favorite_buttons(items, 1, set()))
    await message.answer(text, reply_markup=with_home(markup, language))


def create_router() -> Router:
    router = Router(name="listing_card")
    router.callback_query.register(on_recommend, RecommendCallback.filter())
    return router
