import pytest

from bina.application.ports.scraper import RawListing
from bina.infrastructure.scrapers.normalizer import ListingNormalizer


def test_normalize_real_world_data():
    """Тест нормализации с реальными данными."""
    normalizer = ListingNormalizer()
    
    # Тест с грузинскими символами и разными форматами
    raw_listing = RawListing(
        source_id="real123",
        source_name="myhome",
        title="საცხოვრებელი ბინა ვაკეში - სათაური",
        description="აღწერა ქართულად. 2 ოთახიანი ბინა 50 მ²",
        price=1250.50,
        currency="GEL",
        rooms=2,
        area=50.0,
        district="ვაკის რაიონი",
        url="https://www.myhome.ge/ru/123456",
        photos=["https://example.com/photo.jpg"],
    )
    
    normalized = normalizer.normalize_listing(raw_listing)
    assert normalized is not None
    assert normalized.district == "Vake"
    assert "საცხოვრებელი" in normalized.title
    assert normalized.price == 1250.50
    assert normalized.currency == "GEL"


def test_normalize_price_with_symbols():
    """Тест нормализации цены с валютными символами."""
    normalizer = ListingNormalizer()
    
    # Тест с символом лари
    price, currency = normalizer.normalize_price(1000.0, "₾")
    assert price == 1000.0
    assert currency == "GEL"
    
    # Тест с символом доллара
    price, currency = normalizer.normalize_price(500.0, "$")
    assert currency == "GEL"
    assert price > 500.0  # Должно быть конвертировано