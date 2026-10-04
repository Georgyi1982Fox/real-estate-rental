"""«Вам может понравиться» и «Поделиться квартирой» для Mini App (TASK-076, TASK-073).

- ``GET /api/recommendations`` — квартиры, похожие на избранное.
- ``GET /api/listings/{id}/share`` — ссылка на квартиру в боте и окно Telegram «Переслать».
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from bina.application.recommendations import RECOMMENDATIONS_LIMIT
from bina.application.sharing import share_link, telegram_share_url
from bina.application.use_cases.recommendations import RecommendUseCase
from bina.infrastructure.api.dependencies import (
    CurrentUserDep,
    OptionalUserDep,
    SessionDep,
    SettingsDep,
)
from bina.infrastructure.api.routes.common import get_visible_listing_or_404
from bina.infrastructure.api.routes.referral import bot_username_or_none
from bina.infrastructure.api.schemas import ListingOut
from bina.infrastructure.bot.formatters import listing_price, listing_title
from bina.infrastructure.db.repositories.districts import DistrictsRepository
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository

router = APIRouter(tags=["recommendations"])


class RecommendationsOut(BaseModel):
    items: list[ListingOut]
    based_on: int = Field(description="Сколько избранного учтено; 0 — избранного нет")


class ShareOut(BaseModel):
    url: str = Field(description="Ссылка на квартиру в боте (карточка с фото и кнопками)")
    text: str = Field(description="Подпись: заголовок и цена на языке пользователя")
    telegram_url: str = Field(description="Окно Telegram «Переслать» с этой ссылкой")


@router.get("/api/recommendations", response_model=RecommendationsOut)
async def recommendations(
    user: CurrentUserDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=30)] = RECOMMENDATIONS_LIMIT,
) -> RecommendationsOut:
    """Квартиры, похожие на избранное: те же город и вид аренды, близкие район, комнаты, цена."""
    items, based_on = await RecommendUseCase(
        FavoritesRepository(session), ListingsRepository(session), DistrictsRepository(session)
    ).execute(user.id, limit)
    return RecommendationsOut(
        items=[ListingOut.from_model(item) for item in items], based_on=based_on
    )


@router.get("/api/listings/{listing_id}/share", response_model=ShareOut)
async def share(
    listing_id: str,
    request: Request,
    user: OptionalUserDep,
    session: SessionDep,
    settings: SettingsDep,
    lang: Annotated[str | None, Query(pattern="^(ka|ru|en)$")] = None,
) -> ShareOut:
    """Поделиться квартирой. 503 — бот не настроен (ссылку собрать не из чего)."""
    listing = await get_visible_listing_or_404(session, listing_id)
    username = await bot_username_or_none(request, settings)
    if not username:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Bot is not configured")
    language = lang or (user.language if user else "ru")
    link = share_link(username, listing.id)
    text = f"{listing_title(listing, language)} · {listing_price(listing, language)}"
    return ShareOut(url=link, text=text, telegram_url=telegram_share_url(link, text))
