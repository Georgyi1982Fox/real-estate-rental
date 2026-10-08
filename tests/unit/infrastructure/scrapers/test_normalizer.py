import pytest

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.normalizer import ListingNormalizer


def test_normalize_price_gel() -> None:
    """Тест нормализации цены в GEL."""
    normalizer = ListingNormalizer()
    price, currency = normalizer.normalize_price(1000.0, "GEL")
    assert price == 1000.0
    assert currency == "GEL"


def test_normalize_price_usd() -> None:
    """Тест нормализации цены из USD в GEL."""
    normalizer = ListingNormalizer()
    price, currency = normalizer.normalize_price(1000.0, "USD")
    # Приблизительный курс 2.7
    assert price == pytest.approx(2700.0, rel=0.1)
    assert currency == "GEL"


def test_normalize_price_eur() -> None:
    """Тест нормализации цены из EUR в GEL."""
    normalizer = ListingNormalizer()
    price, currency = normalizer.normalize_price(1000.0, "EUR")
    # Приблизительный курс 3.0
    assert price == pytest.approx(3000.0, rel=0.1)
    assert currency == "GEL"


def test_clean_text() -> None:
    """Тест очистки текста."""
    normalizer = ListingNormalizer()
    cleaned = normalizer.clean_text("   Hello   World!   ")
    assert cleaned == "Hello World"


def test_normalize_district_georgian() -> None:
    """Тест нормализации грузинского района."""
    normalizer = ListingNormalizer()
    normalized = normalizer.normalize_district("ვაკე")
    assert normalized == "Vake"


def test_normalize_district_english() -> None:
    """Тест нормализации английского района."""
    normalizer = ListingNormalizer()
    normalized = normalizer.normalize_district("Vake")
    assert normalized == "Vake"


def test_validate_fields_valid() -> None:
    """Тест валидации корректных полей."""
    normalizer = ListingNormalizer()
    listing = RawListing(
        source_id="123",
        source_name="test",
        title="Test",
        description="Test description",
        price=1000.0,
        currency="GEL",
        rooms=2,
        area=50.0,
        district="Vake",
        url="https://example.com",
        photos=[],
    )
    assert normalizer.validate_fields(listing) is True


def test_validate_fields_invalid_price() -> None:
    """Тест валидации с некорректной ценой."""
    normalizer = ListingNormalizer()
    listing = RawListing(
        source_id="123",
        source_name="test",
        title="Test",
        description="Test description",
        price=-100.0,
        currency="GEL",
        rooms=2,
        area=50.0,
        district="Vake",
        url="https://example.com",
        photos=[],
    )
    assert normalizer.validate_fields(listing) is False


def test_normalize_listing_complete() -> None:
    """Тест полной нормализации объявления."""
    normalizer = ListingNormalizer()
    raw_listing = RawListing(
        source_id="123",
        source_name="myhome",
        title="   Test Title   ",
        description="   Test Description   ",
        price=1000.0,
        currency="USD",
        rooms=2,
        area=50.0,
        district="ვაკე",
        url="https://example.com",
        photos=["https://example.com/photo.jpg"],
    )

    normalized = normalizer.normalize_listing(raw_listing)
    assert normalized is not None
    assert normalized.title == "Test Title"
    assert normalized.description == "Test Description"
    assert normalized.price > 1000.0  # Должно быть конвертировано в GEL
    assert normalized.currency == "GEL"
    assert normalized.district == "Vake"


def korter_card(description: str, **fields: object) -> RawListing:
    values: dict[str, object] = {
        "source_id": "936575",
        "source_name": "korter",
        "title": "1-комн. квартира, Ваке, 33 м²",
        "description": description,
        "price": 800.0,
        "currency": "GEL",
        "rooms": 1,
        "area": 33.0,
        "district": "Ваке",
        "url": "https://korter.ge/ru/a/936575",
        "city": "tbilisi",
        "latitude": 41.71,
        "longitude": 44.75,
    }
    values.update(fields)
    return RawListing(**values)  # type: ignore[arg-type]


def test_listing_moves_to_city_named_in_text() -> None:
    """Korter.ge: батумская квартира в разделе Тбилиси — переносится в Батуми."""
    normalizer = ListingNormalizer()
    card = korter_card("🏠 Сдается 1-комнатная квартира в Батуми — Orbi City, Блок C")

    fixed = normalizer.normalize_listing(card)

    assert fixed is not None
    assert (fixed.city, fixed.district) == ("batumi", "Батуми")
    assert (fixed.latitude, fixed.longitude) == (None, None)


@pytest.mark.parametrize(
    "description",
    [
        "Сдается квартира в Тбилиси, Ваке",
        "Квартира на улице Батуми, рядом метро",
        "Квартира в Тбилиси. Есть и в Батуми",
        "Уютная квартира. " + "Тихий двор. " * 20 + "Удобный выезд в Мцхета.",
    ],
)
def test_listing_keeps_its_city(description: str) -> None:
    fixed = ListingNormalizer().normalize_listing(korter_card(description))

    assert fixed is not None
    assert (fixed.city, fixed.district, fixed.latitude) == ("tbilisi", "Ваке", 41.71)


def test_georgian_text_names_city() -> None:
    card = korter_card("ქირავდება 1 ოთახიანი ბინა ბათუმში, შერიფ ხიმშიაშვილის ქუჩა")

    fixed = ListingNormalizer().normalize_listing(card)

    assert fixed is not None and fixed.city == "batumi"


@pytest.mark.parametrize(
    ("price", "period"), [(150.0, "daily"), (1000.0, "daily"), (4860.0, "monthly")]
)
def test_daily_price_too_high_is_monthly(price: float, period: str) -> None:
    card = korter_card("Сдается квартира посуточно", rent_period="daily", price=price)

    fixed = ListingNormalizer().normalize_listing(card)

    assert fixed is not None and fixed.rent_period == period


@pytest.mark.parametrize(
    ("price", "area", "kept"),
    [(2025.0, 70.0, True), (325488.0, 70.0, False), (13500.0, 70.0, True), (150000.0, 0.0, False)],
)
def test_sale_price_in_rent_listing_is_skipped(price: float, area: float, kept: bool) -> None:
    """325 488 ₾ в месяц за 70 м² — цена продажи, такое объявление не сохраняется."""
    card = korter_card("Сдается квартира", price=price, area=area)

    fixed = ListingNormalizer().normalize_listing(card)

    assert (fixed is not None) is kept


@pytest.mark.parametrize(
    ("price", "period", "expected"),
    [
        (1.0, "monthly", None),  # цена не указана
        (10.0, "daily", None),
        (60.0, "monthly", "daily"),  # Бакуриани: 60 ₾ — за сутки
        (150.0, "monthly", "monthly"),
        (450.0, "monthly", "monthly"),
    ],
)
def test_too_low_prices(price: float, period: str, expected: str | None) -> None:
    card = korter_card("Сдается квартира", price=price, rent_period=period)

    fixed = ListingNormalizer().normalize_listing(card)

    assert (fixed.rent_period if fixed else None) == expected


@pytest.mark.parametrize(
    ("area", "rooms", "expected"),
    [(1400.0, 4, 140.0), (700.0, 2, 70.0), (800.0, 7, 800.0), (90.0, 3, 90.0)],
)
def test_extra_zero_in_area(area: float, rooms: int, expected: float) -> None:
    card = korter_card("Сдается квартира", area=area, rooms=rooms, price=3000.0)

    fixed = ListingNormalizer().normalize_listing(card)

    assert fixed is not None and fixed.area == expected
