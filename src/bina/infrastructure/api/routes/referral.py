"""Приглашение друзей (TASK-108).

- ``GET /api/referral`` — ссылка приглашения, сколько приглашено и наград.
- ``POST /api/referral/apply`` ``{"code": "…"}`` — Mini App открыли по ссылке
  ``startapp=ref_<код>``: запомнить пригласившего (только в первые сутки после
  регистрации и если ещё не платил).
"""

from datetime import UTC, datetime

import structlog
from aiogram import Bot
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from bina.application.referrals import (
    APPLY_WINDOW,
    FRIEND_DISCOUNT_PERCENT,
    MONTHLY_REWARDS,
    REWARD_DAYS,
    START_PREFIX,
    code_from_start,
    invite_link,
    month_start,
)
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep, SettingsDep
from bina.infrastructure.api.routes.common import bad_request
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.repositories.referrals import ReferralsRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/referral", tags=["referral"])


class ReferralOut(BaseModel):
    code: str
    link: str
    invited: int
    rewarded: int
    rewarded_this_month: int
    monthly_limit: int = MONTHLY_REWARDS
    reward_days: int = REWARD_DAYS
    friend_discount_percent: int = FRIEND_DISCOUNT_PERCENT


class ApplyIn(BaseModel):
    code: str = Field(min_length=1, max_length=40, description="Код или ``ref_<код>``")


class ApplyOut(BaseModel):
    applied: bool
    discount_percent: int


async def bot_username(request: Request, settings: ApiSettings) -> str:
    """Имя бота для ссылки: из настроек, иначе из Telegram (один раз, затем из памяти)."""
    cached: str | None = getattr(request.app.state, "bot_username", None)
    if cached:
        return cached
    if not settings.bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bot is not configured"
        )
    bot = Bot(token=settings.bot_token)
    try:
        me = await bot.get_me()
    finally:
        await bot.session.close()
    request.app.state.bot_username = me.username or ""
    return request.app.state.bot_username  # type: ignore[no-any-return]


async def bot_username_or_none(request: Request, settings: ApiSettings) -> str | None:
    """Имя бота или ``None``, если бот не настроен или Telegram недоступен."""
    try:
        return await bot_username(request, settings) or None
    except HTTPException:
        return None
    except Exception as exc:  # noqa: BLE001 - нет связи с Telegram: работаем без ссылки на бота
        logger.warning("Bot username not resolved", error=str(exc))
        return None


@router.get("", response_model=ReferralOut)
async def my_referral(
    request: Request, user: CurrentUserDep, session: SessionDep, settings: SettingsDep
) -> ReferralOut:
    referrals = ReferralsRepository(session)
    code = await referrals.code_for(user)
    await session.commit()
    invited, rewarded, recent = await referrals.stats(user.id, month_start(datetime.now(UTC)))
    return ReferralOut(
        code=code,
        link=invite_link(await bot_username(request, settings), code),
        invited=invited,
        rewarded=rewarded,
        rewarded_this_month=recent,
    )


@router.post("/apply", response_model=ApplyOut)
async def apply_referral(body: ApplyIn, user: CurrentUserDep, session: SessionDep) -> ApplyOut:
    raw = body.code.strip()
    code = code_from_start(raw if raw.startswith(START_PREFIX) else START_PREFIX + raw)
    if code is None:
        raise bad_request("invalid referral code")
    referrals = ReferralsRepository(session)
    referrer = await referrals.by_code(code)
    if referrer is None:
        raise bad_request("invalid referral code")
    applied = False
    if datetime.now(UTC) - user.created_at <= APPLY_WINDOW:
        applied = await referrals.set_referrer(user, referrer)
        await session.commit()
    discount = await referrals.discount_eligible(user)
    return ApplyOut(applied=applied, discount_percent=FRIEND_DISCOUNT_PERCENT if discount else 0)
