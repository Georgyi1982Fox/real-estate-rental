import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    and_,
    case,
    cast,
    func,
    literal_column,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from bina.application.costs import GEL_RATES
from bina.application.dtos.listing_search import ListingSearchFilters, ListingSort
from bina.application.duplicates import candidate_bounds
from bina.application.fraud import HIDE_SCORE
from bina.application.listing_details import clean_features
from bina.application.localization import district_names, script_of
from bina.application.ports.scraper import RawListing
from bina.application.ports.translator import LANGUAGES, ListingText
from bina.application.price_analysis import ROOMS_GROUP_MAX
from bina.application.repositories.listings import IListingsRepository
from bina.application.repositories.notifications import PriceDrop
from bina.infrastructure.db.models import (
    District,
    Embedding,
    Favorite,
    Listing,
    ListingStatus,
    ScrapeSkip,
    User,
)
from bina.infrastructure.db.repositories.users import premium_access_now

if TYPE_CHECKING:
    from collections.abc import Sequence


# Меньше объявлений в районе — медиана цены ненадёжна (TASK-011)
MIN_MEDIAN_SAMPLES = 5


@dataclass(frozen=True, slots=True)
class DistrictStats:
    """Статистика района по объявлениям в поиске; цены — в лари."""

    listings: int
    # Медиана аренды по комнатам (4 — «4 и больше»); только где объявлений достаточно
    median_rent: dict[int, Decimal]
    median_per_m2: Decimal | None


class ListingsRepository(IListingsRepository):
    """Реализация репозитория объявлений."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_listings_by_district(
        self,
        district_id: UUID,
        limit: int,
    ) -> list[Listing]:
        """Получить активные объявления по району."""
        query = (
            select(Listing)
            .where(
                Listing.district_id == district_id,
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
            )
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )

        result = await self._session.execute(query)
        listings: Sequence[Listing] = result.scalars().all()
        return list(listings)

    async def get_by_id(self, listing_id: UUID) -> Listing | None:
        """Получить объявление по ID."""
        query = select(Listing).where(Listing.id == listing_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def find_by_source(
        self,
        source_id: str,
        source_name: str,
    ) -> Listing | None:
        """Найти объявление по source_id и source_name."""
        query = select(Listing).where(
            Listing.source_id == source_id,
            Listing.source_name == source_name,
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def save_translation(
        self,
        listing_id: UUID,
        title_ru: str,
        description_ru: str,
    ) -> None:
        """Сохранить перевод объявления."""
        query = (
            update(Listing)
            .where(Listing.id == listing_id)
            .values(title_ru=title_ru, description_ru=description_ru)
        )
        await self._session.execute(query)

    async def search(
        self,
        filters: ListingSearchFilters,
        limit: int,
        offset: int = 0,
        sort: ListingSort = ListingSort.NEWEST,
    ) -> list[Listing]:
        """Найти активные объявления по фильтрам в порядке ``sort`` (по умолчанию новые сверху)."""
        query = (
            select(Listing)
            .where(*self._search_conditions(filters))
            .order_by(*_sort_order(sort, filters), FRESHNESS.desc(), Listing.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def semantic_search(
        self,
        filters: ListingSearchFilters,
        vector: list[float],
        model: str,
        limit: int,
        offset: int = 0,
    ) -> list[Listing]:
        """Объявления с отпечатком ``model`` по близости к ``vector`` (TASK-012)."""
        query = (
            select(Listing)
            .join(Embedding, Embedding.listing_id == Listing.id)
            .where(*self._search_conditions(filters), Embedding.model_name == model)
            .order_by(Embedding.vector.cosine_distance(vector), Listing.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def semantic_count(self, filters: ListingSearchFilters, model: str) -> int:
        """Сколько объявлений под фильтрами уже имеют отпечаток ``model``."""
        query = (
            select(func.count())
            .select_from(Listing)
            .join(Embedding, Embedding.listing_id == Listing.id)
            .where(*self._search_conditions(filters), Embedding.model_name == model)
        )
        return int((await self._session.execute(query)).scalar_one())

    async def count(self, filters: ListingSearchFilters) -> int:
        """Количество активных объявлений, подходящих под фильтры."""
        query = select(func.count()).select_from(Listing).where(*self._search_conditions(filters))
        result = await self._session.execute(query)
        return int(result.scalar_one())

    @staticmethod
    def _search_conditions(filters: ListingSearchFilters) -> list[ColumnElement[bool]]:
        """Собирает условия WHERE для поиска по фильтрам."""
        conditions: list[ColumnElement[bool]] = [
            Listing.status == ListingStatus.ACTIVE,
            Listing.is_deleted.is_(False),
            # TASK-011: почти наверняка мошенники — не в поиске и не в уведомлениях
            Listing.fraud_score < HIDE_SCORE,
            # TASK-106: скрыто жалобами или модератором
            Listing.hidden_at.is_(None),
            # TASK-090: та же квартира с другого сайта показывается один раз
            not_hidden_duplicate(),
        ]
        if filters.city is not None:
            conditions.append(
                Listing.district_id.in_(select(District.id).where(District.city == filters.city))
            )
        district_ids = filters.all_district_ids
        if len(district_ids) == 1:
            conditions.append(Listing.district_id == district_ids[0])
        elif district_ids:
            conditions.append(Listing.district_id.in_(district_ids))
        if filters.price_min is not None:
            conditions.append(Listing.price >= filters.price_min)
        if filters.price_max is not None:
            conditions.append(Listing.price <= filters.price_max)
        if filters.rooms_min is not None:
            conditions.append(Listing.rooms >= filters.rooms_min)
        if filters.rooms_max is not None:
            conditions.append(Listing.rooms <= filters.rooms_max)
        if filters.area_min is not None:
            conditions.append(Listing.area >= filters.area_min)
        if filters.area_max is not None:
            conditions.append(Listing.area <= filters.area_max)
        conditions.extend(_detail_conditions(filters))
        # Запрос без слов (только знаки) не фильтрует — как пустая строка поиска
        ts_query = text_search_query(filters.query) if filters.query else None
        if ts_query is not None:
            conditions.append(SEARCH_VECTOR.op("@@")(ts_query))
        return conditions

    async def create_or_update_from_raw(
        self,
        raw_listing: RawListing,
    ) -> Listing:
        """Создать или обновить объявление из RawListing.

        Заголовок и описания попадают в колонки того языка, на котором они
        **написаны** (TASK-019): на русской странице сайта описание бывает на
        грузинском. Переводы на другие языки при обновлении сохраняются, если
        исходный текст не изменился.
        """
        district = await self._get_or_create_district(raw_listing.district, raw_listing.city)
        texts = source_texts(raw_listing)
        values: dict[str, object] = {
            **texts,
            "price": Decimal(str(raw_listing.price)),
            "currency": raw_listing.currency,
            "rooms": raw_listing.rooms,
            "area": Decimal(str(raw_listing.area)),
            "district_id": district.id,
            "images": list(raw_listing.photos),
            "url": raw_listing.url or None,
            "phone": raw_listing.phone,
            "owner_name": raw_listing.owner_name,
            # Страница объявления может сказать, что оно уже снято
            "status": ListingStatus.ACTIVE if raw_listing.active else ListingStatus.ARCHIVED,
            "is_deleted": False,
            "checked_at": datetime.now(UTC),
        }

        listing = await self.find_by_source(raw_listing.source_id, raw_listing.source_name)
        if (
            listing is not None
            and listing.details_fetched_at is not None
            and not raw_listing.has_details
        ):
            # Страница объявления не загрузилась: краткий текст из списка (у SS обрезан)
            # не должен затирать полный, а удобства — пропадать
            for column in [key for key in texts if key.startswith("description_")]:
                values.pop(column)
                del texts[column]
            values.pop("images")
            if not raw_listing.phone:
                values.pop("phone")
        else:
            values.update(detail_values(raw_listing))
        values.update(source_dates(raw_listing))
        if listing is not None:
            photos = values.get("images", listing.images)
            text_changed = source_text_changed(listing, texts)
            if text_changed:
                values.update(stale_translation_resets(texts))
            new_price = values["price"]
            price_changed = listing.price is not None and Decimal(listing.price) != new_price
            if price_changed:
                # Для уведомления «цена снижена» (TASK-028)
                values["previous_price"] = listing.price
                values["price_changed_at"] = datetime.now(UTC)
                # С новой ценой дубликаты могут быть другими (TASK-090)
                values["duplicates_checked_at"] = None
            if text_changed or price_changed or bool(listing.images) != bool(photos):
                values["fraud_checked_at"] = None
        if listing is None:
            listing = Listing(
                source_id=raw_listing.source_id,
                source_name=raw_listing.source_name,
                # Второй язык заполнит перевод (TranslateListingUseCase)
                title_ru="",
                title_ka="",
                description_ru="",
                description_ka="",
                title_en="",
                description_en="",
            )
            self._session.add(listing)
        for key, value in values.items():
            setattr(listing, key, value)

        await self._session.flush()  # ID нужен для embeddings
        return listing

    async def source_snapshot(self, source_name: str) -> list[Any]:
        """Цена, статус и даты всех объявлений источника (строки ``source_id, ...``)."""
        query = select(
            Listing.source_id,
            Listing.price,
            Listing.status,
            Listing.details_fetched_at,
            Listing.source_updated_at,
        ).where(Listing.source_name == source_name, Listing.is_deleted.is_(False))
        return list((await self._session.execute(query)).all())

    async def list_duplicates_unchecked(self, limit: int) -> list[Listing]:
        """Активные объявления, для которых ещё не искали дубликаты (старые первыми).

        Старые первыми: основным становится объявление, появившееся раньше.
        """
        query = (
            select(Listing)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                Listing.duplicates_checked_at.is_(None),
            )
            .order_by(Listing.created_at, Listing.id)
            .limit(limit)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def duplicate_candidates(self, listing: Listing) -> list[Listing]:
        """Активные объявления того же района с теми же комнатами, похожей площадью и ценой."""
        bounds = candidate_bounds(listing)
        query = (
            select(Listing)
            .where(
                Listing.id != listing.id,
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                Listing.district_id == listing.district_id,
                Listing.rooms == listing.rooms,
                Listing.currency == listing.currency,
                Listing.area.between(bounds.area_min, bounds.area_max),
                Listing.price.between(bounds.price_min, bounds.price_max),
            )
            .order_by(Listing.created_at, Listing.id)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def mark_duplicate(self, listing_id: UUID, primary_id: UUID) -> None:
        """Объявление — дубликат ``primary_id``."""
        await self._session.execute(
            update(Listing).where(Listing.id == listing_id).values(duplicate_of=primary_id)
        )

    async def mark_duplicates_checked(self, listing_ids: list[UUID]) -> None:
        """Дубликаты для этих объявлений искали."""
        if listing_ids:
            await self._session.execute(
                update(Listing)
                .where(Listing.id.in_(listing_ids))
                .values(duplicates_checked_at=datetime.now(UTC))
            )

    async def same_apartment_links(self, listing: Listing) -> list[tuple[str, str]]:
        """Сайты и ссылки той же квартиры: основное объявление и его дубликаты (активные)."""
        primary_id = listing.duplicate_of or listing.id
        query = (
            select(Listing.source_name, Listing.url)
            .where(
                or_(Listing.id == primary_id, Listing.duplicate_of == primary_id),
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                Listing.url.is_not(None),
            )
            .order_by(Listing.created_at)
        )
        return [(str(source), str(url)) for source, url in (await self._session.execute(query))]

    async def source_stats(self) -> list[tuple[str, str, int]]:
        """Сколько объявлений у каждого источника в каждом статусе."""
        query = (
            select(Listing.source_name, Listing.status, func.count())
            .where(Listing.is_deleted.is_(False))
            .group_by(Listing.source_name, Listing.status)
            .order_by(Listing.source_name, Listing.status)
        )
        rows = (await self._session.execute(query)).all()
        return [
            (str(source), ListingStatus(status).value, int(count)) for source, status, count in rows
        ]

    async def recent_skips(self, source_name: str, since: datetime) -> set[str]:
        """ID объявлений источника, пропущенных после ``since`` (TASK-091)."""
        query = select(ScrapeSkip.source_id).where(
            ScrapeSkip.source_name == source_name, ScrapeSkip.skipped_at >= since
        )
        return set((await self._session.execute(query)).scalars())

    async def add_skips(self, source_name: str, source_ids: list[str]) -> None:
        """Запомнить пропущенные объявления (повторно разбирать не нужно)."""
        if not source_ids:
            return
        rows = [{"source_name": source_name, "source_id": item} for item in source_ids]
        await self._session.execute(
            pg_insert(ScrapeSkip)
            .values(rows)
            .on_conflict_do_update(
                index_elements=["source_name", "source_id"], set_={"skipped_at": func.now()}
            )
        )

    async def archive_published_before(self, source_name: str, before: datetime) -> int:
        """Снять объявления источника, опубликованные раньше ``before`` (старые посты)."""
        result = await self._session.execute(
            update(Listing)
            .where(
                Listing.source_name == source_name,
                Listing.status == ListingStatus.ACTIVE,
                func.coalesce(Listing.source_published_at, Listing.created_at) < before,
            )
            .values(status=ListingStatus.ARCHIVED)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def mark_checked(self, source_name: str, source_ids: list[str]) -> None:
        """Объявления видели на сайте сейчас (в списке): откладывает их повторную проверку."""
        if not source_ids:
            return
        await self._session.execute(
            update(Listing)
            .where(Listing.source_name == source_name, Listing.source_id.in_(source_ids))
            .values(checked_at=datetime.now(UTC))
        )

    async def search_created_since(
        self, filters: ListingSearchFilters, since: datetime, limit: int
    ) -> list[Listing]:
        """Активные объявления под фильтры, появившиеся после ``since`` (новые сверху)."""
        query = (
            select(Listing)
            .where(*self._search_conditions(filters), Listing.created_at > since)
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def count_created_since(self, filters: ListingSearchFilters, since: datetime) -> int:
        """Сколько активных объявлений под фильтры появилось после ``since``."""
        query = (
            select(func.count())
            .select_from(Listing)
            .where(*self._search_conditions(filters), Listing.created_at > since)
        )
        return int((await self._session.execute(query)).scalar_one())

    async def favorite_price_drops(
        self, since: datetime, *, premium_only: bool = False
    ) -> list[PriceDrop]:
        """Подешевевшие после ``since`` объявления из избранного пользователей.

        ``premium_only`` — только у пользователей с действующим Premium (TASK-085).
        """
        query = (
            select(Favorite.user_id, Listing)
            .join(Listing, Listing.id == Favorite.listing_id)
            .join(User, User.id == Favorite.user_id)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                User.is_deleted.is_(False),
                Listing.price_changed_at > since,
                Listing.previous_price > Listing.price,
            )
        )
        if premium_only:
            query = query.where(premium_access_now())
        rows = (await self._session.execute(query)).all()
        # previous_price не NULL (условие выше), проверка — для типов
        return [
            PriceDrop(user_id=user_id, listing=listing, old_price=listing.previous_price)
            for user_id, listing in rows
            if listing.previous_price is not None
        ]

    async def list_untranslated(self, limit: int) -> list[Listing]:
        """Активные объявления без заголовка или без описания хотя бы на одном языке.

        Без описания — только если оно есть на другом языке (иначе переводить нечего).
        Новые сверху.
        """
        query = (
            select(Listing)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                _untranslated(),
                # Скрытые дубликаты не показываются — переводить их незачем (TASK-090)
                not_hidden_duplicate(),
            )
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def language_coverage(self) -> tuple[int, int]:
        """Активных объявлений всего и сколько из них ещё ждут перевода."""
        active = and_(
            Listing.status == ListingStatus.ACTIVE,
            Listing.is_deleted.is_(False),
            not_hidden_duplicate(),
        )
        query = select(
            func.count().filter(active),
            func.count().filter(and_(active, _untranslated())),
        )
        total, missing = (await self._session.execute(query)).one()
        return int(total), int(missing)

    async def save_texts(self, listing_id: UUID, texts: dict[str, ListingText]) -> None:
        """Записать переводы только в пустые поля.

        Текст, который уже есть (с сайта на этом языке или от прошлого перевода),
        не заменяется: переводятся только недостающие заголовки и описания.
        """
        values: dict[str, Any] = {}
        for language, text in texts.items():
            if language not in LANGUAGES:
                continue
            for kind, value in (("title", text.title), ("description", text.description)):
                column = getattr(Listing, f"{kind}_{language}")
                values[f"{kind}_{language}"] = case(
                    (func.coalesce(column, "") == "", value), else_=column
                )
        if values:
            await self._session.execute(
                update(Listing).where(Listing.id == listing_id).values(**values)
            )

    # ------------------------------------------------------------- TASK-011: антифрод

    async def list_fraud_unchecked(self, limit: int) -> list[Listing]:
        """Активные объявления без проверки на мошенничество (новые сверху), с районом."""
        query = (
            select(Listing)
            .options(selectinload(Listing.district))
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                Listing.fraud_checked_at.is_(None),
            )
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def district_median_per_m2(self, district_id: UUID, currency: str) -> Decimal | None:
        """Медиана цены за м² активных объявлений района в той же валюте.

        None, если объявлений меньше :data:`MIN_MEDIAN_SAMPLES`: сравнивать не с чем.
        """
        per_m2 = Listing.price / Listing.area
        query = select(
            func.count(),
            func.percentile_cont(0.5).within_group(per_m2),
        ).where(
            Listing.district_id == district_id,
            Listing.currency == currency,
            Listing.status == ListingStatus.ACTIVE,
            Listing.is_deleted.is_(False),
            Listing.area > 0,
            Listing.price > 0,
        )
        count, median = (await self._session.execute(query)).one()
        if count < MIN_MEDIAN_SAMPLES or median is None:
            return None
        return Decimal(str(median))

    async def rooms_median_price(
        self, district_id: UUID, rooms: int, currency: str
    ) -> tuple[int, Decimal | None]:
        """Сколько видимых объявлений района с этим числом комнат (4+ вместе) и медиана цены."""
        rooms_condition = (
            Listing.rooms >= ROOMS_GROUP_MAX if rooms >= ROOMS_GROUP_MAX else Listing.rooms == rooms
        )
        query = select(func.count(), func.percentile_cont(0.5).within_group(Listing.price)).where(
            *self._visible(),
            Listing.district_id == district_id,
            Listing.currency == currency,
            Listing.price > 0,
            rooms_condition,
        )
        count, median = (await self._session.execute(query)).one()
        return int(count), Decimal(str(median)) if median is not None else None

    async def district_price_per_m2(
        self, district_id: UUID, currency: str
    ) -> tuple[int, Decimal | None]:
        """Сколько видимых объявлений района с площадью и медиана цены за м²."""
        query = select(
            func.count(), func.percentile_cont(0.5).within_group(Listing.price / Listing.area)
        ).where(
            *self._visible(),
            Listing.district_id == district_id,
            Listing.currency == currency,
            Listing.price > 0,
            Listing.area > 0,
        )
        count, median = (await self._session.execute(query)).one()
        return int(count), Decimal(str(median)) if median is not None else None

    async def cheaper_similar(self, listing: Listing, limit: int) -> list[Listing]:
        """Похожие и дешевле (TASK-095): тот же район и комнаты, площадь ±20%, цена ниже."""
        area = Decimal(str(listing.area or 0))
        rooms_condition = (
            Listing.rooms >= ROOMS_GROUP_MAX
            if listing.rooms >= ROOMS_GROUP_MAX
            else Listing.rooms == listing.rooms
        )
        query = (
            select(Listing)
            .options(selectinload(Listing.district))
            .where(
                *self._visible(),
                Listing.id != listing.id,
                Listing.district_id == listing.district_id,
                Listing.currency == listing.currency,
                Listing.price < listing.price,
                Listing.price > 0,
                rooms_condition,
                Listing.area.between(area * Decimal("0.8"), area * Decimal("1.2")),
            )
            .order_by(Listing.price, Listing.id)
            .limit(limit)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def district_stats(self, district_id: UUID) -> DistrictStats:
        """Объявления района в поиске: сколько их и медианы цен в лари (TASK-104)."""
        rate = case(
            *((Listing.currency == code, value) for code, value in GEL_RATES.items()),
            else_=None,
        )
        price_gel = Listing.price * rate
        bucket = func.least(Listing.rooms, ROOMS_GROUP_MAX).label("bucket")
        visible = [*self._visible(), Listing.district_id == district_id, Listing.price > 0]
        median = func.percentile_cont(0.5).within_group(price_gel)
        rows = (
            await self._session.execute(
                select(bucket, func.count(), median).where(*visible).group_by(bucket)
            )
        ).all()
        per_m2: float | None = (
            await self._session.execute(
                select(func.percentile_cont(0.5).within_group(price_gel / Listing.area)).where(
                    *visible, Listing.area > 0
                )
            )
        ).scalar_one()
        return DistrictStats(
            listings=sum(int(count) for _, count, _ in rows),
            median_rent={
                int(rooms): Decimal(str(value)).quantize(Decimal(1))
                for rooms, count, value in rows
                if value is not None and count >= MIN_MEDIAN_SAMPLES
            },
            median_per_m2=(
                Decimal(str(per_m2)).quantize(Decimal("0.1")) if per_m2 is not None else None
            ),
        )

    async def to_geocode(self, limit: int) -> list[Listing]:
        """Объявления без координат, но с адресом, которые ещё не искали на карте (TASK-080)."""
        query = (
            select(Listing)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                Listing.latitude.is_(None),
                Listing.address.is_not(None),
                Listing.address != "",
                Listing.geocoded_at.is_(None),
            )
            .options(selectinload(Listing.district))
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(query)).scalars().all())

    async def save_location(self, listing_id: UUID, location: tuple[float, float] | None) -> None:
        """Записать найденную точку (или отметить, что искали и не нашли)."""
        values: dict[str, Any] = {"geocoded_at": datetime.now(UTC)}
        if location is not None:
            values["latitude"], values["longitude"] = location
        await self._session.execute(
            update(Listing).where(Listing.id == listing_id).values(**values)
        )

    @staticmethod
    def _visible() -> list[ColumnElement[bool]]:
        """Объявления, которые видит пользователь (для статистики цен)."""
        return [
            Listing.status == ListingStatus.ACTIVE,
            Listing.is_deleted.is_(False),
            Listing.fraud_score < HIDE_SCORE,
            Listing.hidden_at.is_(None),
            not_hidden_duplicate(),
        ]

    async def save_fraud(self, listing_id: UUID, score: int, reasons: list[str]) -> None:
        """Записать оценку и время проверки."""
        await self._session.execute(
            update(Listing)
            .where(Listing.id == listing_id)
            .values(
                fraud_score=score,
                fraud_reasons=list(reasons),
                fraud_checked_at=datetime.now(UTC),
            )
        )

    async def _get_or_create_district(self, district_name: str, city: str) -> District:
        """Район города по названию; нового района ещё нет — создаётся."""
        from bina.infrastructure.db.repositories.districts import DistrictsRepository

        districts_repo = DistrictsRepository(self._session)
        # Сайты пишут по-разному («Старий Тбилиси»): ищем и по словарным названиям (TASK-019)
        for candidate in dict.fromkeys([district_name, *district_names(district_name).values()]):
            district = await districts_repo.get_by_name(candidate, city)
            if district is not None:
                return district
        return await districts_repo.create_district(district_name, city)


def _untranslated() -> ColumnElement[bool]:
    """Нет заголовка на каком-то языке или нет описания (при том что на другом оно есть)."""
    descriptions = [getattr(Listing, f"description_{language}") for language in LANGUAGES]
    has_description = or_(*(func.coalesce(column, "") != "" for column in descriptions))
    return or_(
        *(func.coalesce(getattr(Listing, f"title_{language}"), "") == "" for language in LANGUAGES),
        and_(has_description, or_(*(func.coalesce(column, "") == "" for column in descriptions))),
    )


def not_hidden_duplicate() -> ColumnElement[bool]:
    """Не дубликат, или его основное объявление уже не в поиске (TASK-090).

    Основное снято с сайта или скрыто (антифрод, жалобы) — тогда показывается дубликат.
    """
    primary = aliased(Listing)
    visible_primary = (
        select(primary.id)
        .where(
            primary.id == Listing.duplicate_of,
            primary.status == ListingStatus.ACTIVE,
            primary.is_deleted.is_(False),
            primary.fraud_score < HIDE_SCORE,
            primary.hidden_at.is_(None),
        )
        .exists()
    )
    return or_(Listing.duplicate_of.is_(None), ~visible_primary)


def source_texts(raw: RawListing) -> dict[str, str]:
    """Колонки текстов из источника по языку, на котором текст написан.

    Заголовок и основное описание — по письменности (грузинская, кириллица,
    латиница); пустые не записываются. Описания, которые сайт дал сам на других
    языках (SS.ge), занимают свободные языки.
    """
    default = "ka" if raw.language == "ka" else "ru"
    title_lang = script_of(raw.title) if raw.title.strip() else default
    texts: dict[str, str] = {}
    if raw.title.strip():
        texts[f"title_{title_lang}"] = raw.title
    for text in (raw.description, *raw.descriptions.values()):
        if text and text.strip():
            column = f"description_{script_of(text)}"
            texts.setdefault(column, text)
    return texts


def source_text_changed(listing: Listing, texts: dict[str, str]) -> bool:
    """Изменился ли текст с сайта (тогда старые переводы неверны)."""
    return any((getattr(listing, column, "") or "") != text for column, text in texts.items())


def stale_translation_resets(texts: dict[str, str]) -> dict[str, str]:
    """Пустые тексты во всех колонках, кроме пришедших с сайта: их заново переведёт AI."""
    return {
        f"{kind}_{language}": ""
        for kind in ("title", "description")
        for language in LANGUAGES
        if f"{kind}_{language}" not in texts
    }


def detail_values(raw: RawListing) -> dict[str, object]:
    """Подробности объявления для записи в БД.

    Со страницы объявления — все поля (и отметка ``details_fetched_at``); из списка —
    только то, что в нём есть.
    """
    fields: dict[str, object] = {
        "floor": raw.floor,
        "total_floors": raw.total_floors,
        "bedrooms": raw.bedrooms,
        "bathrooms": raw.bathrooms,
        "condition": raw.condition,
        "owner_type": raw.owner_type,
        "address": raw.address,
        "latitude": raw.latitude,
        "longitude": raw.longitude,
    }
    if raw.has_details:
        fields["features"] = clean_features(raw.features)
        fields["details_fetched_at"] = datetime.now(UTC)
        return fields
    values = {key: value for key, value in fields.items() if value is not None}
    if raw.features:
        values["features"] = clean_features(raw.features)
    return values


def source_dates(raw: RawListing) -> dict[str, object]:
    """Даты публикации и обновления на сайте (если источник их дал)."""
    dates: dict[str, object] = {}
    if raw.published_at is not None:
        dates["source_published_at"] = raw.published_at
    if raw.updated_at is not None:
        dates["source_updated_at"] = raw.updated_at
    return dates


# «Новые сверху»: дата обновления на сайте, для объявлений без неё — дата появления у нас
FRESHNESS = func.coalesce(Listing.source_updated_at, Listing.created_at)


def _detail_conditions(filters: ListingSearchFilters) -> list[ColumnElement[bool]]:
    """Условия по подробностям объявления (TASK-018).

    Объявления, у которых нужного поля нет (сайт не указал этаж), под такой
    фильтр не попадают.
    """
    conditions: list[ColumnElement[bool]] = []
    if filters.floor_min is not None:
        conditions.append(Listing.floor >= filters.floor_min)
    if filters.floor_max is not None:
        conditions.append(Listing.floor <= filters.floor_max)
    if filters.not_first_floor:
        conditions.append(Listing.floor > 1)
    if filters.not_last_floor:
        conditions.append(Listing.floor < Listing.total_floors)
    if filters.bedrooms_min is not None:
        conditions.append(Listing.bedrooms >= filters.bedrooms_min)
    if filters.bathrooms_min is not None:
        conditions.append(Listing.bathrooms >= filters.bathrooms_min)
    if filters.features:
        conditions.append(cast(Listing.features, JSONB).contains(list(filters.features)))
    if filters.conditions:
        conditions.append(Listing.condition.in_(filters.conditions))
    if filters.owner_only:
        conditions.append(Listing.owner_type == "owner")
    if filters.published_since is not None:
        published = func.coalesce(Listing.source_published_at, Listing.created_at)
        conditions.append(published >= filters.published_since)
    if filters.sources:
        conditions.append(Listing.source_name.in_(filters.sources))
    return conditions


def _sort_order(sort: ListingSort, filters: ListingSearchFilters) -> list[Any]:
    """ORDER BY для ``sort``; дальше всегда новые сверху (стабильная пагинация)."""
    if sort is ListingSort.RELEVANCE:
        ts_query = text_search_query(filters.query) if filters.query else None
        if ts_query is None:
            return []
        return [func.ts_rank(SEARCH_VECTOR, ts_query).desc()]
    if sort is ListingSort.PRICE_ASC:
        return [Listing.price.asc()]
    if sort is ListingSort.PRICE_DESC:
        return [Listing.price.desc()]
    if sort is ListingSort.AREA_DESC:
        return [Listing.area.desc()]
    if sort is ListingSort.PRICE_PER_M2_ASC:
        # Без площади цена за м² неизвестна — такие в конце
        return [(Listing.price / func.nullif(Listing.area, 0)).asc().nulls_last()]
    return []


# ---------------------------------------------------------------- TASK-022: поиск

# Вычисляемый столбец из миграции listing_search_vector (в модели не описан: его пишет PostgreSQL)
SEARCH_VECTOR = literal_column("bina_listings.search_vector", type_=TSVECTOR)
# Словари: русский и английский — со словоформами, грузинский — как есть
SEARCH_CONFIGS = ("russian", "english", "simple")
MAX_QUERY_WORDS = 8
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def text_search_query(text: str) -> ColumnElement[Any] | None:
    """tsquery для текста поиска: все слова (по началу слова), любой из словарей.

    «сабурт 2 комнаты» → ``сабурт:* & 2:* & комнаты:*`` в русском, английском и
    простом словаре, объединённые через OR. В запросе остаются только буквы и цифры,
    поэтому спецсимволы tsquery (``& | ! :``) из пользовательского текста невозможны.
    ``None``, если слов нет.
    """
    words = _WORD_RE.findall(text.lower())[:MAX_QUERY_WORDS]
    if not words:
        return None
    expression = " & ".join(f"{word}:*" for word in words)
    queries = [
        func.to_tsquery(literal_column(f"'{config}'::regconfig"), expression)
        for config in SEARCH_CONFIGS
    ]
    combined: ColumnElement[Any] = queries[0]
    for query in queries[1:]:
        combined = combined.op("||")(query)
    return combined
