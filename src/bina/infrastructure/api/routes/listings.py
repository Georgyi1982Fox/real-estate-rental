"""Объявления: список с фильтрами, карточка, похожие, телефон и контакт."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import ValidationError

from bina.application.dtos.listing_search import (
    SOURCES,
    ListingSearchFilters,
    ListingSort,
    search_filters,
)
from bina.application.listing_details import CONDITIONS, FEATURES
from bina.application.owner_listings import OWNER_SOURCE
from bina.application.ports.embeddings import EmbeddingsError, IEmbedder
from bina.application.risk_report import risk_report
from bina.application.semantic_search import is_smart_query
from bina.application.subscriptions import has_premium_access
from bina.application.use_cases.analyze_price import AnalyzePriceUseCase
from bina.application.use_cases.search_listings import SearchListingsUseCase
from bina.application.use_cases.smart_search import SmartSearchUseCase
from bina.infrastructure.api.dependencies import CurrentUserDep, OptionalUserDep, SessionDep
from bina.infrastructure.api.routes.common import (
    MAX_PER_PAGE,
    bad_request,
    get_listing_or_404,
    get_visible_listing_or_404,
    not_found,
    parse_codes,
    parse_decimal,
    parse_districts,
    valid_city,
)
from bina.infrastructure.api.schemas import (
    CityCode,
    ContactOut,
    ListingOut,
    ListingsOut,
    ListingsPageOut,
    PhoneOut,
    PriceAnalysisOut,
    RentPeriod,
    RiskOut,
    SourceLinkOut,
)
from bina.infrastructure.api.validation import clean_text
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.agencies import ListingStatsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.llm.llm_factory import LLMFactory, embeddings_configured

router = APIRouter(prefix="/api/listings", tags=["listings"])
logger = structlog.get_logger(__name__)

SIMILAR_LIMIT = 3
SIMILAR_PRICE_SPREAD = Decimal("0.3")


@router.get("", response_model=ListingsPageOut)
async def list_listings(
    request: Request,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=MAX_PER_PAGE)] = 20,
    city: Annotated[
        CityCode | None, Query(description="Код города (см. /api/cities); пусто — все (TASK-079)")
    ] = None,
    rent_period: Annotated[
        RentPeriod,
        Query(description="TASK-092: monthly (по умолчанию) или daily — посуточно, цена за сутки"),
    ] = "monthly",
    district: Annotated[
        list[str] | None,
        Query(
            description="ID района; несколько — повтором (district=a&district=b) или через запятую"
        ),
    ] = None,
    min_price: Annotated[str | None, Query()] = None,
    max_price: Annotated[str | None, Query()] = None,
    rooms: Annotated[int | None, Query(ge=1, description="4 = «4 и больше»")] = None,
    min_area: Annotated[str | None, Query(description="Площадь от, м²")] = None,
    max_area: Annotated[str | None, Query(description="Площадь до, м²")] = None,
    q: Annotated[
        str | None,
        Query(max_length=100, description="Текст поиска: заголовок и описание (ru, ka, en)"),
    ] = None,
    floor_min: Annotated[int | None, Query(ge=0, le=100, description="Этаж от")] = None,
    floor_max: Annotated[int | None, Query(ge=0, le=100, description="Этаж до")] = None,
    not_first_floor: Annotated[bool, Query(description="Не первый этаж")] = False,
    not_last_floor: Annotated[bool, Query(description="Не последний этаж")] = False,
    bedrooms: Annotated[int | None, Query(ge=1, le=10, description="Спален от")] = None,
    bathrooms: Annotated[int | None, Query(ge=1, le=10, description="Санузлов от")] = None,
    features: Annotated[
        str | None,
        Query(description="Удобства через запятую, нужны все: furniture,air_conditioning,..."),
    ] = None,
    condition: Annotated[
        str | None,
        Query(description="Состояние через запятую, любое из: newly_renovated,renovated,..."),
    ] = None,
    owner_only: Annotated[bool, Query(description="Только собственники, без агентств")] = False,
    published_days: Annotated[
        int | None, Query(ge=1, le=365, description="Опубликовано за последние N дней")
    ] = None,
    source: Annotated[
        str | None,
        Query(
            description="Источники через запятую, любой из: ss, myhome, livo, korter, telegram, "
            "owner (собственники, TASK-096)"
        ),
    ] = None,
    sort: Annotated[
        ListingSort | None,
        Query(
            description="newest, relevance, smart, price_asc, price_desc, area_desc, "
            "price_per_m2_asc. smart — по смыслу q (умный поиск, TASK-012; если AI недоступен — "
            "как relevance). По умолчанию: relevance, если задан q, иначе newest"
        ),
    ] = None,
) -> ListingsPageOut:
    """Активные объявления с пагинацией, фильтрами, поиском по тексту и сортировкой."""
    valid_city(city)
    try:
        filters = search_filters(
            city=city,
            rent_period=rent_period,
            district_ids=parse_districts(district),
            price_min=parse_decimal(min_price, "min_price"),
            price_max=parse_decimal(max_price, "max_price"),
            rooms=rooms,
            area_min=parse_decimal(min_area, "min_area"),
            area_max=parse_decimal(max_area, "max_area"),
            query=clean_text(q) if q else None,
            floor_min=floor_min,
            floor_max=floor_max,
            not_first_floor=not_first_floor,
            not_last_floor=not_last_floor,
            bedrooms_min=bedrooms,
            bathrooms_min=bathrooms,
            features=parse_codes(features, FEATURES, "features"),
            conditions=parse_codes(condition, CONDITIONS, "condition"),
            owner_only=owner_only,
            published_since=(
                datetime.now(UTC) - timedelta(days=published_days) if published_days else None
            ),
            sources=parse_codes(source, SOURCES, "source"),
        )
    except ValidationError as exc:
        raise bad_request(
            "min_price must be <= max_price, min_area <= max_area, floor_min <= floor_max"
        ) from exc

    if sort is ListingSort.SMART and is_smart_query(filters.query):
        embedder = get_embedder(request)
        if embedder is not None:
            try:
                smart = await SmartSearchUseCase(ListingsRepository(session), embedder).execute(
                    filters, page=page - 1, page_size=per_page
                )
                return ListingsPageOut.from_page(smart)
            except EmbeddingsError as exc:
                logger.warning("Smart search unavailable, falling back", error=str(exc))
        sort = ListingSort.RELEVANCE
    elif sort is ListingSort.SMART:
        sort = None
    result = await SearchListingsUseCase(ListingsRepository(session)).execute(
        filters,
        page=page - 1,
        page_size=per_page,
        sort=sort or (ListingSort.RELEVANCE if filters.query else ListingSort.NEWEST),
    )
    return ListingsPageOut.from_page(result)


def get_embedder(request: Request) -> IEmbedder | None:
    """Embeddings для умного поиска; в тестах — ``app.state.embedder``; без ключа — None."""
    injected: IEmbedder | None = getattr(request.app.state, "embedder", None)
    if injected is not None:
        return injected
    if not embeddings_configured():
        return None
    embedder: IEmbedder = LLMFactory.create_embeddings_provider()
    request.app.state.embedder = embedder
    return embedder


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(listing_id: str, session: SessionDep) -> ListingOut:
    """Одно объявление; 404, если его нет или оно удалено."""
    listing = await get_listing_or_404(session, listing_id)
    # TASK-100: просмотр — в статистику хозяина / агентства
    await ListingStatsRepository(session).record(listing, datetime.now(UTC).date(), view=True)
    await session.commit()
    out = ListingOut.from_model(listing)
    # TASK-090: ссылки на ту же квартиру на других сайтах
    links = await ListingsRepository(session).same_apartment_links(listing)
    out.also_on = [
        SourceLinkOut(source=source, url=url) for source, url in links if url != listing.url
    ]
    return out


@router.get("/{listing_id}/price", response_model=PriceAnalysisOut)
async def price_analysis(
    listing_id: str, user: CurrentUserDep, session: SessionDep
) -> PriceAnalysisOut:
    """Дешевле или дороже обычного для района (TASK-093).

    Оценка — всем; проценты, обычная цена и выборка — только Premium.
    """
    listing = await get_listing_or_404(session, listing_id)
    analysis = await AnalyzePriceUseCase(ListingsRepository(session)).execute(listing)
    return PriceAnalysisOut.build(
        analysis, listing.currency, premium=has_premium_access(user, datetime.now(UTC))
    )


@router.get("/{listing_id}/risk", response_model=RiskOut)
async def risk(listing_id: str, user: CurrentUserDep, session: SessionDep) -> RiskOut:
    """Разбор риска (TASK-094): уровень и причины — всем, объяснения и советы — Premium."""
    listing = await get_listing_or_404(session, listing_id)
    report = risk_report(listing.fraud_score or 0, list(listing.fraud_reasons or []), user.language)
    return RiskOut.build(report, premium=has_premium_access(user, datetime.now(UTC)))


@router.get("/{listing_id}/similar", response_model=ListingsOut)
async def similar_listings(listing_id: str, session: SessionDep) -> ListingsOut:
    """До трёх похожих активных объявлений.

    Кандидаты по убыванию похожести: тот же район с ценой ±30%, затем тот же
    район с любой ценой, затем другие районы с ценой ±30%.
    """
    listing = await get_listing_or_404(session, listing_id)
    price_min = listing.price * (1 - SIMILAR_PRICE_SPREAD)
    price_max = listing.price * (1 + SIMILAR_PRICE_SPREAD)
    # Похожие — того же вида аренды (посуточные к посуточным, TASK-092)
    period = listing.rent_period
    tiers = (
        ListingSearchFilters(
            district_id=listing.district_id,
            price_min=price_min,
            price_max=price_max,
            rent_period=period,
        ),
        ListingSearchFilters(district_id=listing.district_id, rent_period=period),
        ListingSearchFilters(price_min=price_min, price_max=price_max, rent_period=period),
    )

    repository = ListingsRepository(session)
    seen = {listing.id}
    items: list[Listing] = []
    for filters in tiers:
        for candidate in await repository.search(filters, limit=SIMILAR_LIMIT + len(seen)):
            if candidate.id not in seen:
                seen.add(candidate.id)
                items.append(candidate)
        if len(items) >= SIMILAR_LIMIT:
            break
    return ListingsOut(items=[ListingOut.from_model(item) for item in items[:SIMILAR_LIMIT]])


@router.get("/{listing_id}/phone", response_model=PhoneOut)
async def listing_phone(listing_id: str, user: OptionalUserDep, session: SessionDep) -> PhoneOut:
    """Телефон арендодателя; 404, если его нет или объявление не в поиске.

    Сайты-источники часто скрывают номер (MyHome отдаёт ``591589***``), такие не сохраняются:
    тогда фронтенд показывает кнопку «Написать» (ссылка на объявление на сайте).
    Номер хозяина, разместившего объявление у нас, — только вошедшим через Telegram (401):
    иначе номера всех хозяев можно собрать скриптом.
    """
    listing = await get_visible_listing_or_404(session, listing_id)
    if user is None and listing.source_name == OWNER_SOURCE:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Log in with Telegram to see the phone")
    await ListingStatsRepository(session).record(listing, datetime.now(UTC).date())
    await session.commit()
    if not listing.phone:
        raise not_found("Phone not available")
    return PhoneOut(phone=listing.phone)


@router.post("/{listing_id}/contact", response_model=ContactOut)
async def listing_contact(listing_id: str, session: SessionDep) -> ContactOut:
    """Ссылка для связи с арендодателем: страница объявления на сайте-источнике."""
    listing = await get_visible_listing_or_404(session, listing_id)
    await ListingStatsRepository(session).record(listing, datetime.now(UTC).date())
    await session.commit()
    if not listing.url:
        raise not_found("Contact not available")
    return ContactOut(url=listing.url)
