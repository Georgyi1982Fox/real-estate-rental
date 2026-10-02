"""Продвижение объявления и проверка собственника (TASK-097, TASK-098). Не коммитит."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import structlog

from bina.application.owner_listings import (
    ALREADY_VERIFIED,
    NOT_ACTIVE,
    NOT_FOUND,
    VERIFICATION_PENDING,
    OwnerListingError,
)
from bina.application.promotion import (
    PROMOTION_PLAN,
    VerificationStatus,
    extended_promotion,
    listing_from_payload,
    promotion_price,
)
from bina.application.subscriptions import STARS_CURRENCY
from bina.infrastructure.db.models import Listing, ListingStatus, User, Verification
from bina.infrastructure.db.repositories.owner_listings import OwnerListingsRepository
from bina.infrastructure.db.repositories.payments import PaymentsRepository
from bina.infrastructure.db.repositories.users import UsersRepository
from bina.infrastructure.db.repositories.verifications import VerificationsRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PromotionResult:
    listing: Listing
    until: datetime
    # False — платёж уже учтён (Telegram прислал его повторно)
    activated: bool


@dataclass(frozen=True, slots=True)
class Decision:
    verification: Verification
    listing: Listing
    owner: User


class PromotionUseCase:
    def __init__(self, listings: OwnerListingsRepository, payments: PaymentsRepository) -> None:
        self._listings = listings
        self._payments = payments

    async def promotable(self, user_id: UUID, listing_id: UUID) -> Listing:
        """Своё объявление в поиске; иначе :class:`OwnerListingError`."""
        listing = await self._listings.get_owned(user_id, listing_id)
        if listing is None:
            raise OwnerListingError(NOT_FOUND)
        if listing.status != ListingStatus.ACTIVE or listing.hidden_at is not None:
            raise OwnerListingError(NOT_ACTIVE)
        return listing

    async def check_payment(self, user_id: UUID, payload: str, currency: str, amount: int) -> bool:
        """Перед списанием: объявление своё и в поиске, сумма и валюта верны."""
        listing_id = listing_from_payload(payload)
        if listing_id is None or currency != STARS_CURRENCY or amount != promotion_price():
            return False
        try:
            await self.promotable(user_id, listing_id)
        except OwnerListingError:
            return False
        return True

    async def activate(
        self, user_id: UUID, payload: str, charge_id: str, amount: int, now: datetime
    ) -> PromotionResult | None:
        """Деньги списаны: записать платёж и продвинуть. ``None`` — объявление не найдено."""
        listing_id = listing_from_payload(payload)
        listing = (
            await self._listings.get_owned(user_id, listing_id) if listing_id is not None else None
        )
        if listing is None:
            return None
        if await self._payments.exists(charge_id):
            logger.info("Promotion payment already processed", charge_id=charge_id)
            until = listing.promoted_until or now
            return PromotionResult(listing, until, activated=False)
        until = extended_promotion(listing.promoted_until, now)
        await self._payments.add_success(
            user_id=user_id,
            amount=Decimal(amount),
            currency=STARS_CURRENCY,
            provider_payment_id=charge_id,
            plan=PROMOTION_PLAN,
        )
        await self._listings.set_promotion(listing, until, now)
        logger.info("Listing promoted", listing_id=str(listing.id), until=until)
        return PromotionResult(listing, until, activated=True)


class VerificationUseCase:
    def __init__(
        self,
        listings: OwnerListingsRepository,
        verifications: VerificationsRepository,
        users: UsersRepository,
    ) -> None:
        self._listings = listings
        self._verifications = verifications
        self._users = users

    async def can_request(self, user_id: UUID, listing_id: UUID) -> Listing:
        listing = await self._listings.get_owned(user_id, listing_id)
        if listing is None:
            raise OwnerListingError(NOT_FOUND)
        if listing.is_verified:
            raise OwnerListingError(ALREADY_VERIFIED)
        if await self._verifications.pending_for(listing.id) is not None:
            raise OwnerListingError(VERIFICATION_PENDING)
        return listing

    async def request(
        self, user_id: UUID, listing_id: UUID, file_id: str, file_kind: str, now: datetime
    ) -> tuple[Verification, Listing]:
        listing = await self.can_request(user_id, listing_id)
        verification = await self._verifications.add(listing.id, user_id, file_id, file_kind, now)
        return verification, listing

    async def decide(self, verification_id: UUID, approve: bool, now: datetime) -> Decision:
        """Решение владельца сервиса; повторное нажатие — :class:`OwnerListingError`."""
        verification = await self._verifications.get(verification_id)
        if verification is None or verification.status != VerificationStatus.PENDING:
            raise OwnerListingError(NOT_FOUND)
        listing = await self._listings.get_owned(verification.user_id, verification.listing_id)
        owner = await self._users.get_by_id(verification.user_id)
        if listing is None or owner is None:
            await self._verifications.decide(verification, VerificationStatus.REJECTED, now)
            raise OwnerListingError(NOT_FOUND)
        status = VerificationStatus.APPROVED if approve else VerificationStatus.REJECTED
        await self._verifications.decide(verification, status, now)
        if approve:
            await self._listings.set_verified(listing)
        return Decision(verification, listing, owner)
