"""Кабинет риелтора / агентства и страница агентства для Mini App (TASK-100).

- ``GET /api/agency`` — свой кабинет: пакет, лимит, статистика объявлений; 404 — не риелтор.
- ``POST /api/agency`` — зарегистрироваться риелтором (сразу, без одобрения).
- ``PATCH /api/agency`` — название и описание; ``POST /api/agency/logo`` — логотип (тело —
  картинка).
- ``GET /api/agencies/{id}`` — страница агентства для всех: описание и объявления.

Оплата пакетов и Premium-объявлений — звёздами в боте (Mini App открывает бота).
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from bina.application.agencies import (
    BUMP_DAYS,
    MAX_DESCRIPTION,
    PLAN_DAYS,
    bump_price,
    clean_name,
    free_listings,
    load_agency_plans,
    plan_active,
)
from bina.application.owner_listings import OwnerListingError, clean_phone
from bina.application.ports.photo_storage import PhotoError
from bina.application.subscriptions import premium_for_all
from bina.application.use_cases.agencies import AgencyUseCase
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import bad_request, not_found
from bina.infrastructure.api.schemas import ListingOut
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.db.models import Agency, ListingStatus
from bina.infrastructure.db.repositories.agencies import AgenciesRepository, ListingStats
from bina.infrastructure.storage.photos import MAX_PHOTO_BYTES, LocalPhotoStorage

router = APIRouter(tags=["agency"])


class AgencyPlanOut(BaseModel):
    id: str
    listings: int
    price_stars: int
    days: int


class ListingStatsOut(BaseModel):
    listing: ListingOut
    active: bool
    views: int
    contacts: int
    chats: int
    viewings: int
    favorites: int
    premium_until: datetime | None = None


class AgencyOut(BaseModel):
    """Свой кабинет. Статистика — за 30 дней."""

    id: UUID
    name: str
    description: str
    phone: str | None
    logo_url: str | None
    plan: str | None = Field(description="Оплаченный пакет; None — бесплатный")
    plan_expires_at: datetime | None
    testing_mode: bool = Field(description="Всё бесплатно, пока владелец тестирует")
    limit: int = Field(description="Сколько объявлений может быть в поиске")
    active: int = Field(description="Сколько сейчас в поиске")
    free_listings: int
    plans: list[AgencyPlanOut]
    plan_days: int = PLAN_DAYS
    bump_price_stars: int
    bump_days: int = BUMP_DAYS
    blocked: bool
    listings: list[ListingStatsOut]


class AgencyIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=MAX_DESCRIPTION)
    phone: str | None = Field(default=None, max_length=30)


class AgencyPatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION)


class AgencyPageOut(BaseModel):
    """Страница агентства для всех."""

    id: UUID
    name: str
    description: str
    logo_url: str | None
    listings: list[ListingOut]


def _stats_out(item: ListingStats, now: datetime) -> ListingStatsOut:
    listing = item.listing
    until = listing.bump_until
    return ListingStatsOut(
        listing=ListingOut.from_model(listing),
        active=listing.status == ListingStatus.ACTIVE and listing.hidden_at is None,
        views=item.views,
        contacts=item.contacts,
        chats=item.chats,
        viewings=item.viewings,
        favorites=item.favorites,
        premium_until=until if until is not None and until > now else None,
    )


async def _agency_out(session: SessionDep, agency: Agency, user_id: UUID) -> AgencyOut:
    now = datetime.now(UTC)
    agencies = AgenciesRepository(session)
    plans = load_agency_plans()
    stats = await agencies.stats(user_id, now.date())
    out = [_stats_out(item, now) for item in stats]
    return AgencyOut(
        id=agency.id,
        name=agency.name,
        description=agency.description,
        phone=agency.phone,
        logo_url=agency.logo_url,
        plan=agency.plan if plan_active(agency.plan, agency.plan_expires_at, now) else None,
        plan_expires_at=agency.plan_expires_at,
        testing_mode=premium_for_all(),
        limit=await AgencyUseCase(agencies, plans).active_limit(user_id, now),
        active=sum(item.active for item in out),
        free_listings=free_listings(),
        plans=[
            AgencyPlanOut(id=p.id, listings=p.listings, price_stars=p.price_stars, days=p.days)
            for p in plans.values()
        ],
        bump_price_stars=bump_price(),
        blocked=agency.blocked_at is not None,
        listings=out,
    )


async def _mine(session: SessionDep, user_id: UUID) -> Agency:
    agency = await AgenciesRepository(session).for_user(user_id)
    if agency is None:
        raise not_found("Not a realtor yet")
    return agency


@router.get("/api/agency", response_model=AgencyOut)
async def my_agency(user: CurrentUserDep, session: SessionDep) -> AgencyOut:
    """Свой кабинет; 404 — пользователь ещё не риелтор."""
    agency = await _mine(session, user.id)
    return await _agency_out(session, agency, user.id)


@router.post("/api/agency", response_model=AgencyOut, status_code=status.HTTP_201_CREATED)
async def register_agency(body: AgencyIn, user: CurrentUserDep, session: SessionDep) -> AgencyOut:
    """Стать риелтором (сразу). 409 — кабинет уже есть."""
    name = clean_name(body.name)
    if name is None:
        raise bad_request("name must be 2-80 characters")
    phone = clean_phone(body.phone) if body.phone else None
    if body.phone and phone is None:
        raise bad_request("phone looks invalid")
    use_case = AgencyUseCase(AgenciesRepository(session), load_agency_plans())
    try:
        agency = await use_case.register(
            user.id, name, phone, clean_text(body.description), datetime.now(UTC)
        )
    except OwnerListingError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Agency already exists") from exc
    await session.commit()
    return await _agency_out(session, agency, user.id)


@router.patch("/api/agency", response_model=AgencyOut)
async def update_agency(
    body: AgencyPatchIn, user: CurrentUserDep, session: SessionDep
) -> AgencyOut:
    agency = await _mine(session, user.id)
    if body.name is not None:
        name = clean_name(body.name)
        if name is None:
            raise bad_request("name must be 2-80 characters")
        agency.name = name
    if body.description is not None:
        agency.description = clean_text(body.description)
    await AgenciesRepository(session).save(agency, datetime.now(UTC))
    await session.commit()
    return await _agency_out(session, agency, user.id)


@router.post("/api/agency/logo", response_model=AgencyOut)
async def upload_logo(request: Request, user: CurrentUserDep, session: SessionDep) -> AgencyOut:
    """Логотип: тело — файл картинки."""
    agency = await _mine(session, user.id)
    data = await request.body()
    if not data or len(data) > MAX_PHOTO_BYTES:
        raise bad_request(f"logo must be 1 byte to {MAX_PHOTO_BYTES} bytes")
    storage = LocalPhotoStorage()
    try:
        url = storage.save(f"agency-{agency.id.hex}", data)
    except PhotoError as exc:
        raise bad_request("bad_photo") from exc
    if agency.logo_url:
        storage.delete(agency.logo_url)
    agency.logo_url = url
    await AgenciesRepository(session).save(agency, datetime.now(UTC))
    await session.commit()
    return await _agency_out(session, agency, user.id)


@router.get("/api/agencies/{agency_id}", response_model=AgencyPageOut)
async def agency_page(agency_id: UUID, session: SessionDep) -> AgencyPageOut:
    """Страница агентства: описание и объявления в поиске."""
    agencies = AgenciesRepository(session)
    agency = await agencies.get(agency_id)
    if agency is None or agency.blocked_at is not None:
        raise not_found("Agency not found")
    listings = await agencies.listings(agency.user_id, active_only=True)
    return AgencyPageOut(
        id=agency.id,
        name=agency.name,
        description=agency.description,
        logo_url=agency.logo_url,
        listings=[ListingOut.from_model(listing) for listing in listings],
    )
