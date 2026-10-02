"""Объявления собственников (TASK-096): разбор ответов, заголовки, сценарии."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from bina.application.listing_titles import listing_titles
from bina.application.owner_listings import (
    MAX_ACTIVE_LISTINGS,
    MAX_PHOTOS,
    OwnerListingDraft,
    OwnerListingError,
    clean_phone,
    owner_raw_listing,
    parse_area,
    parse_floor,
    telegram_contact,
    valid_description,
)
from bina.application.ports.photo_storage import PhotoError
from bina.application.use_cases.owner_listings import OwnerListingsUseCase
from bina.infrastructure.db.models import Listing, ListingStatus

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def draft(**fields: Any) -> OwnerListingDraft:
    values: dict[str, Any] = {
        "city": "tbilisi",
        "district": "Ваке",
        "rent_period": "monthly",
        "price": Decimal(1500),
        "currency": "GEL",
        "rooms": 2,
        "area": Decimal(60),
        "description": "Светлая квартира с ремонтом, рядом парк.",
        "phone": "+995555123456",
    }
    values.update(fields)
    return OwnerListingDraft(**values)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("60", Decimal(60)), ("72,5 м²", Decimal("72.5")), ("5", None), ("5000", None), ("", None)],
)
def test_parse_area(text: str, expected: Decimal | None) -> None:
    assert parse_area(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("5/9", (5, 9)), ("5 из 9", (5, 9)), ("3", (3, None)), ("9/5", None), ("abc", None)],
)
def test_parse_floor(text: str, expected: tuple[int, int | None] | None) -> None:
    assert parse_floor(text) == expected


def test_contacts_and_description() -> None:
    assert clean_phone("+995 (555) 12-34-56") == "+995555123456"
    assert clean_phone("позвоните") is None
    assert telegram_contact("nino_home") == "https://t.me/nino_home"
    assert telegram_contact(None) is None
    assert telegram_contact("x y") is None
    assert valid_description("Хорошая квартира у метро, всё есть.")
    assert not valid_description("Сдаю")


def test_titles_in_three_languages() -> None:
    names = {"ru": "Ваке", "en": "Vake", "ka": "ვაკე"}
    assert listing_titles(2, Decimal(60), "monthly", names) == {
        "title_ru": "2-комн. квартира, Ваке, 60 м²",
        "title_en": "2-room apartment, Vake, 60 m²",
        "title_ka": "2-ოთახიანი ბინა, ვაკე, 60 მ²",
    }
    daily = listing_titles(2, Decimal("45.50"), "daily", names)
    assert daily["title_ru"] == "Посуточно: 2-комн. квартира, Ваке, 45.5 м²"


def test_raw_listing() -> None:
    raw = owner_raw_listing(
        draft(contact_url="https://t.me/nino", rent_period="daily"), "abc", ["/p.jpg"], NOW
    )
    assert (raw.source_name, raw.source_id, raw.owner_type) == ("owner", "abc", "owner")
    assert (raw.url, raw.phone, raw.photos) == ("https://t.me/nino", "+995555123456", ["/p.jpg"])
    assert (raw.rent_period, raw.has_details, raw.published_at) == ("daily", True, NOW)


# ------------------------------------------------------------------ сценарии


class FakeRepository:
    def __init__(self) -> None:
        self.listings: list[Listing] = []
        self.user = uuid4()

    async def count_active(self, user_id: UUID) -> int:
        return sum(1 for item in self.listings if item.status == ListingStatus.ACTIVE)

    async def list_for_user(self, user_id: UUID) -> list[Listing]:
        return self.listings

    async def get_owned(self, user_id: UUID, listing_id: UUID) -> Listing | None:
        if user_id != self.user:
            return None
        return next((item for item in self.listings if item.id == listing_id), None)

    async def create(
        self,
        user_id: UUID,
        draft: OwnerListingDraft,
        source_id: str,
        photos: list[str],
        now: datetime,
    ) -> Listing:
        listing = Listing(
            id=uuid4(),
            source_id=source_id,
            images=photos,
            price=draft.price,
            currency=draft.currency,
            status=ListingStatus.ACTIVE,
        )
        self.listings.append(listing)
        return listing

    async def set_active(self, listing: Listing, active: bool, now: datetime) -> None:
        listing.status = ListingStatus.ACTIVE if active else ListingStatus.ARCHIVED

    async def update_price(
        self, listing: Listing, price: Decimal, currency: str, now: datetime
    ) -> None:
        listing.price, listing.currency = price, currency

    async def set_photos(self, listing: Listing, photos: list[str]) -> None:
        listing.images = photos


class FakeStorage:
    def __init__(self) -> None:
        self.saved: list[str] = []
        self.deleted: list[str] = []

    def save(self, folder: str, data: bytes) -> str:
        if data == b"junk":
            raise PhotoError("not an image")
        url = f"/api/media/listings/{folder}/{len(self.saved)}.jpg"
        self.saved.append(url)
        return url

    def delete(self, url: str) -> None:
        self.deleted.append(url)


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def use_case(repository: FakeRepository, storage: FakeStorage) -> OwnerListingsUseCase:
    return OwnerListingsUseCase(repository, storage)


async def test_publish_skips_bad_photos(
    use_case: OwnerListingsUseCase, repository: FakeRepository
) -> None:
    listing = await use_case.publish(repository.user, draft(), [b"a", b"junk", b"b"], NOW)
    assert len(listing.images) == 2
    assert all(
        url.startswith(f"/api/media/listings/{listing.source_id}/") for url in listing.images
    )


async def test_publish_needs_contact_and_respects_limit(
    use_case: OwnerListingsUseCase, repository: FakeRepository
) -> None:
    with pytest.raises(OwnerListingError, match="no_contact"):
        await use_case.publish(repository.user, draft(phone=None), [], NOW)
    for _ in range(MAX_ACTIVE_LISTINGS):
        await use_case.publish(repository.user, draft(), [], NOW)
    with pytest.raises(OwnerListingError, match="limit"):
        await use_case.publish(repository.user, draft(), [], NOW)

    first = repository.listings[0]
    await use_case.set_active(repository.user, first.id, False, NOW)
    await use_case.publish(repository.user, draft(), [], NOW)
    with pytest.raises(OwnerListingError, match="limit"):
        await use_case.set_active(repository.user, first.id, True, NOW)


async def test_photos_and_price(
    use_case: OwnerListingsUseCase, repository: FakeRepository, storage: FakeStorage
) -> None:
    listing = await use_case.publish(repository.user, draft(), [], NOW)
    for _ in range(MAX_PHOTOS):
        await use_case.add_photo(repository.user, listing.id, b"x")
    with pytest.raises(OwnerListingError, match="too_many_photos"):
        await use_case.add_photo(repository.user, listing.id, b"x")

    first = listing.images[0]
    await use_case.delete_photo(repository.user, listing.id, 0)
    assert storage.deleted == [first] and len(listing.images) == MAX_PHOTOS - 1
    with pytest.raises(OwnerListingError, match="bad_photo"):
        await use_case.add_photo(repository.user, listing.id, b"junk")

    await use_case.update_price(repository.user, listing.id, Decimal(1400), "GEL", NOW)
    assert listing.price == Decimal(1400)
    with pytest.raises(OwnerListingError, match="not_found"):
        await use_case.update_price(uuid4(), listing.id, Decimal(1), "GEL", NOW)


def test_title_falls_back_to_russian_district() -> None:
    titles = listing_titles(3, 100.0, None, {"ru": "Дигоми", "en": "", "ka": ""})
    assert titles["title_en"] == "3-room apartment, Дигоми, 100 m²"
    assert titles["title_ka"] == "3-ოთახიანი ბინა, Дигоми, 100 მ²"
