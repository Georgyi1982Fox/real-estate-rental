"""Подписка Premium: тарифы, лимиты и счёт на оплату звёздами (TASK-026/027).

Оплата в Mini App: ``POST /api/subscription/invoice`` → ``Telegram.WebApp.openInvoice(url)``.
Подписку включает бот, получив ``successful_payment`` от Telegram.
"""

from datetime import UTC, datetime

from aiogram import Bot
from fastapi import APIRouter, HTTPException, Request, status

from bina.application.subscriptions import Plan, is_premium, limits_for, price_for
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep, SettingsDep
from bina.infrastructure.api.routes.common import not_found
from bina.infrastructure.api.schemas import InvoiceIn, InvoiceOut, SubscriptionOut
from bina.infrastructure.db.repositories.favorites import FavoritesRepository
from bina.infrastructure.db.repositories.notifications import SavedSearchesRepository
from bina.infrastructure.db.repositories.referrals import ReferralsRepository
from bina.infrastructure.payments import invoice

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


def get_plans(request: Request) -> dict[str, Plan]:
    """Тарифы (``app.state.plans``)."""
    plans: dict[str, Plan] = request.app.state.plans
    return plans


@router.get("", response_model=SubscriptionOut)
async def get_subscription(
    request: Request, user: CurrentUserDep, session: SessionDep
) -> SubscriptionOut:
    """Текущий тариф, срок, лимиты, использование и цены."""
    now = datetime.now(UTC)
    return SubscriptionOut.build(
        user,
        premium=is_premium(user, now),
        limits=limits_for(user, now),
        favorites=await FavoritesRepository(session).count_by_user(user.id),
        searches=await SavedSearchesRepository(session).count_by_user(user.id),
        plans=list(get_plans(request).values()),
        discounted=await ReferralsRepository(session).discount_eligible(user),
    )


@router.post("/invoice", response_model=InvoiceOut)
async def create_invoice(
    body: InvoiceIn,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
) -> InvoiceOut:
    """Ссылка на счёт в звёздах для ``Telegram.WebApp.openInvoice``."""
    plan = get_plans(request).get(body.plan)
    if plan is None:
        raise not_found("Plan not found")
    if not settings.bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payments are not configured"
        )
    discounted = await ReferralsRepository(session).discount_eligible(user)
    bot = Bot(token=settings.bot_token)
    try:
        url = await invoice.create_invoice_link(
            bot, plan, user.language, price_for(plan, discounted)
        )
    finally:
        await bot.session.close()
    return InvoiceOut(url=url)
