"""Кабинет риелтора / агентства (TASK-100). Не коммитит."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import structlog

from bina.application.agencies import (
    BUMP_DAYS,
    BUMP_PLAN,
    BUMPS_PER_AGENCY_PER_RUN,
    AgencyPlan,
    bump_due,
    bump_price,
    extended,
    listing_from_bump_payload,
    listing_limit,
    plan_for_payload,
)
from bina.application.owner_listings import (
    MAX_ACTIVE_LISTINGS,
    NOT_ACTIVE,
    NOT_FOUND,
    OwnerListingError,
)
from bina.application.subscriptions import STARS_CURRENCY, premium_for_all
from bina.infrastructure.db.models import Agency, Listing, ListingStatus
from bina.infrastructure.db.repositories.agencies import AgenciesRepository
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository
from bina.infrastructure.db.repositories.payments import PaymentsRepository

logger = structlog.get_logger(__name__)

# Коды ошибок (тексты — по коду)
ALREADY_REGISTERED = "agency_exists"
BAD_NAME = "agency_name"
BLOCKED = "agency_blocked"


@dataclass(frozen=True, slots=True)
class Paid:
    """Итог оплаты: до какого времени и был ли платёж новым."""

    until: datetime
    activated: bool
    plan: AgencyPlan | None = None
    listing: Listing | None = None


class AgencyUseCase:
    def __init__(
        self,
        agencies: AgenciesRepository,
        plans: dict[str, AgencyPlan],
        payments: PaymentsRepository | None = None,
        listings: OwnerListingsRepository | None = None,
    ) -> None:
        self._agencies = agencies
        self._plans = plans
        self._payments = payments
        self._listings = listings

    async def register(
        self, user_id: UUID, name: str, phone: str | None, description: str, now: datetime
    ) -> Agency:
        if await self._agencies.for_user(user_id) is not None:
            raise OwnerListingError(ALREADY_REGISTERED)
        return await self._agencies.create(user_id, name, phone, description, now)

    async def active_limit(self, user_id: UUID, now: datetime) -> int:
        """Сколько объявлений человек может держать в поиске (хозяин — 5)."""
        agency = await self._agencies.for_user(user_id)
        if agency is None:
            return MAX_ACTIVE_LISTINGS
        if agency.blocked_at is not None:
            return 0
        return listing_limit(self._plans, agency.plan, agency.plan_expires_at, now)

    # --- оплата

    def check_plan_payment(self, payload: str, currency: str, amount: int) -> AgencyPlan | None:
        plan = plan_for_payload(self._plans, payload)
        if plan is None or currency != STARS_CURRENCY or amount != plan.price_stars:
            return None
        return plan

    async def activate_plan(
        self, user_id: UUID, payload: str, charge_id: str, amount: int, now: datetime
    ) -> Paid | None:
        """Пакет оплачен; ``None`` — пакета или агентства нет (разбираться вручную)."""
        assert self._payments is not None
        plan = plan_for_payload(self._plans, payload)
        agency = await self._agencies.for_user(user_id)
        if plan is None or agency is None:
            return None
        if await self._payments.exists(charge_id):
            return Paid(agency.plan_expires_at or now, activated=False, plan=plan)
        # Другой пакет — с сегодняшнего дня; тот же — продление
        current = agency.plan_expires_at if agency.plan == plan.id else None
        agency.plan = plan.id
        agency.plan_expires_at = extended(current, now, plan.days)
        await self._payments.add_success(
            user_id=user_id,
            amount=Decimal(amount),
            currency=STARS_CURRENCY,
            provider_payment_id=charge_id,
            plan=plan.payload,
        )
        await self._agencies.save(agency, now)
        logger.info("Agency plan paid", agency_id=str(agency.id), plan=plan.id)
        return Paid(agency.plan_expires_at, activated=True, plan=plan)

    async def bumpable(self, user_id: UUID, listing_id: UUID) -> Listing:
        """Своё объявление агентства в поиске."""
        assert self._listings is not None
        if await self._agencies.for_user(user_id) is None:
            raise OwnerListingError(NOT_FOUND)
        listing = await self._listings.get_owned(user_id, listing_id)
        if listing is None:
            raise OwnerListingError(NOT_FOUND)
        if listing.status != ListingStatus.ACTIVE or listing.hidden_at is not None:
            raise OwnerListingError(NOT_ACTIVE)
        return listing

    async def check_bump_payment(
        self, user_id: UUID, payload: str, currency: str, amount: int
    ) -> bool:
        listing_id = listing_from_bump_payload(payload)
        if listing_id is None or currency != STARS_CURRENCY or amount != bump_price():
            return False
        try:
            await self.bumpable(user_id, listing_id)
        except OwnerListingError:
            return False
        return True

    async def activate_bump(
        self, user_id: UUID, payload: str, charge_id: str, amount: int, now: datetime
    ) -> Paid | None:
        assert self._payments is not None and self._listings is not None
        listing_id = listing_from_bump_payload(payload)
        listing = (
            await self._listings.get_owned(user_id, listing_id) if listing_id is not None else None
        )
        if listing is None:
            return None
        if await self._payments.exists(charge_id):
            return Paid(listing.bump_until or now, activated=False, listing=listing)
        until = extended(listing.bump_until, now, BUMP_DAYS)
        await self._payments.add_success(
            user_id=user_id,
            amount=Decimal(amount),
            currency=STARS_CURRENCY,
            provider_payment_id=charge_id,
            plan=BUMP_PLAN,
        )
        await self._agencies.set_bump(listing, until)
        return Paid(until, activated=True, listing=listing)

    async def bump_for_free(self, user_id: UUID, listing_id: UUID, now: datetime) -> Paid:
        """Режим тестирования (PREMIUM_FOR_ALL): Premium-объявление без оплаты."""
        assert premium_for_all()
        listing = await self.bumpable(user_id, listing_id)
        until = extended(listing.bump_until, now, BUMP_DAYS)
        await self._agencies.set_bump(listing, until)
        return Paid(until, activated=True, listing=listing)


async def run_bumps(agencies: AgenciesRepository, now: datetime) -> int:
    """Поднимает Premium-объявления, у которых подошло время; сколько подняли."""
    per_owner: Counter[UUID | None] = Counter()
    bumped = 0
    for listing in await agencies.bump_candidates(now):
        if not bump_due(listing.id, listing.bump_until, listing.bumped_at, now):
            continue
        if per_owner[listing.owner_user_id] >= BUMPS_PER_AGENCY_PER_RUN:
            continue
        await agencies.bump(listing, now)
        per_owner[listing.owner_user_id] += 1
        bumped += 1
    return bumped
