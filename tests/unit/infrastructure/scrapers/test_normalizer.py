import pytest

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.normalizer import ListingNormalizer


def test_normalize_price_gel():
    """Тест нормализации цены в GEL."""
    normalizer = ListingNormalizer()
    price, currency = normalizer.normalize_price(1000.0, "GEL")
    assert price == 1000.0
    assert currency == "GEL"


def test_normalize_price_usd():
    """Тест нормализации цены из USD в GEL."""
    normalizer = ListingNormalizer()
    price, currency = normalizer.normalize_price(1000.0, "USD")
    # Приблизительный курс 2.7
    assert price == pytest.approx(2700.0, rel=0.1)
    assert currency == "GEL"


def test_normalize_price_eur():
    """Тест нормализации цены из EUR в GEL."""
    normalizer = ListingNormalizer()
    price, currency = normalizer.normalize_price(1000.0, "EUR")
    # Приблизительный курс 3.0
    assert price == pytest.approx(3000.0, rel=0.1)
    assert currency == "GEL"


def test_clean_text():
    """Тест очистки текста."""
    normalizer = ListingNormalizer()
    cleaned = normalizer.clean_text("   Hello   World!   ")
    assert cleaned == "Hello World"


def test_normalize_district_georgian():
    """Тест нормализации грузинского района."""
    normalizer = ListingNormalizer()
    normalized = normalizer.normalize_district("ვაკე")
    assert normalized == "Vake"


def test_normalize_district_english():
    """Тест нормализации английского района."""
    normalizer = ListingNormalizer()
    normalized = normalizer.normalize_district("Vake")
    assert normalized == "Vake"


def test_validate_fields_valid():
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


def test_validate_fields_invalid_price():
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


def test_normalize_listing_complete():
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