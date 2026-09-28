import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ColumnElement, func, literal_column, or_, select, update
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.dtos.listing_search import ListingSearchFilters, ListingSort
from bina.application.ports.scraper import RawListing
from bina.application.ports.translator import LANGUAGES, ListingText
from bina.application.repositories.listings import IListingsRepository
from bina.application.repositories.notifications import PriceDrop
from bina.infrastructure.db.models import District, Favorite, Listing, ListingStatus, User

if TYPE_CHECKING:
    from collections.abc import Sequence


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
            .order_by(*_sort_order(sort, filters), Listing.created_at.desc(), Listing.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

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
        ]
        if filters.district_id is not None:
            conditions.append(Listing.district_id == filters.district_id)
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

        Текст попадает в ``title_ru``/``description_ru`` или ``*_ka`` по
        ``raw_listing.language``; перевод на другой язык при обновлении сохраняется.
        """
        district = await self._get_or_create_district(raw_listing.district)
        suffix = "ka" if raw_listing.language == "ka" else "ru"
        values: dict[str, object] = {
            f"title_{suffix}": raw_listing.title,
            f"description_{suffix}": raw_listing.description,
            "price": Decimal(str(raw_listing.price)),
            "currency": raw_listing.currency,
            "rooms": raw_listing.rooms,
            "area": Decimal(str(raw_listing.area)),
            "district_id": district.id,
            "images": list(raw_listing.photos),
            "url": raw_listing.url or None,
            "phone": raw_listing.phone,
            "owner_name": raw_listing.owner_name,
            "status": ListingStatus.ACTIVE,
            "is_deleted": False,
        }

        listing = await self.find_by_source(raw_listing.source_id, raw_listing.source_name)
        if listing is not None:
            values.update(
                stale_translation_resets(
                    listing, suffix, raw_listing.title, raw_listing.description
                )
            )
            new_price = values["price"]
            if listing.price is not None and Decimal(listing.price) != new_price:
                # Для уведомления «цена снижена» (TASK-028)
                values["previous_price"] = listing.price
                values["price_changed_at"] = datetime.now(UTC)
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

    async def favorite_price_drops(self, since: datetime) -> list[PriceDrop]:
        """Подешевевшие после ``since`` объявления из избранного пользователей."""
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
        rows = (await self._session.execute(query)).all()
        # previous_price не NULL (условие выше), проверка — для типов
        return [
            PriceDrop(user_id=user_id, listing=listing, old_price=listing.previous_price)
            for user_id, listing in rows
            if listing.previous_price is not None
        ]

    async def list_untranslated(self, limit: int) -> list[Listing]:
        """Активные объявления с пустым заголовком хотя бы на одном языке (новые сверху)."""
        query = (
            select(Listing)
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.is_deleted.is_(False),
                or_(*(getattr(Listing, f"title_{language}") == "" for language in LANGUAGES)),
            )
            .order_by(Listing.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def save_texts(self, listing_id: UUID, texts: dict[str, ListingText]) -> None:
        """Записать заголовок и описание для каждого языка из ``texts``."""
        values: dict[str, str] = {}
        for language, text in texts.items():
            if language in LANGUAGES:
                values[f"title_{language}"] = text.title
                values[f"description_{language}"] = text.description
        if values:
            await self._session.execute(
                update(Listing).where(Listing.id == listing_id).values(**values)
            )

    async def _get_or_create_district(self, district_name: str) -> District:
        """Получает или создает район."""
        # В реальной реализации нужно добавить репозиторий районов
        # Пока вернем первый найденный район или создадим заглушку
        from bina.infrastructure.db.repositories.districts import DistrictsRepository

        districts_repo = DistrictsRepository(self._session)
        district = await districts_repo.get_by_name(district_name)
        if district is None:
            district = await districts_repo.create_district(district_name)
        return district


def stale_translation_resets(
    listing: Listing, language: str, title: str, description: str
) -> dict[str, str]:
    """Пустые поля других языков, если исходный текст объявления изменился.

    Перевод старого текста больше не верен: после сброса его заново сделает
    ``TranslateListingsUseCase``. Если текст тот же, переводы остаются.
    """
    old = (
        getattr(listing, f"title_{language}", "") or "",
        getattr(listing, f"description_{language}", "") or "",
    )
    if old == (title, description):
        return {}
    resets: dict[str, str] = {}
    for other in LANGUAGES:
        if other != language:
            resets[f"title_{other}"] = ""
            resets[f"description_{other}"] = ""
    return resets


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
