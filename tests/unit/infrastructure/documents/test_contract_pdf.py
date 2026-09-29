"""PDF договора аренды (TASK-101): файл собирается со шрифтом с грузинскими буквами."""

from datetime import date
from decimal import Decimal

import pytest

from bina.application.contract import ContractData, Utilities
from bina.infrastructure.documents.contract_pdf import render_contract


@pytest.mark.parametrize("second", ["ru", "en"])
def test_render_contract(second: str) -> None:
    pdf = render_contract(
        ContractData(
            landlord_name="Гиорги Беридзе",
            tenant_name="Anna Smith",
            address="ул. Чавчавадзе 10",
            rooms=2,
            area=60,
            start=date(2026, 11, 1),
            months=12,
            rent=Decimal(1500),
            currency="GEL",
            deposit=Decimal(1500),
            payment_day=5,
            utilities=Utilities.TENANT,
            pets_allowed=False,
            notes="Парковка включена",
        ),
        second,
        today=date(2026, 10, 1),
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 10_000
    # Шрифт DejaVu встроен в файл
    assert b"DejaVu" in pdf
