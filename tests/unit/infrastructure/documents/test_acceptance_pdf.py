"""PDF акта приёмки (TASK-102)."""

from datetime import date

import pytest

from bina.application.acceptance import ITEMS, AcceptanceData, CheckedItem, ItemStatus
from bina.infrastructure.documents.acceptance_pdf import render_acceptance


@pytest.mark.parametrize("second", ["ru", "en"])
def test_render_acceptance(second: str) -> None:
    pdf = render_acceptance(
        AcceptanceData(
            landlord_name="Гиорги Беридзе",
            tenant_name="Anna Smith",
            address="ул. Чавчавадзе 10",
            handover_date=date(2026, 11, 1),
            items=tuple(CheckedItem(code, ItemStatus.OK, "") for code in ITEMS),
            keys=2,
            electricity="12345",
        ),
        second,
    )
    assert pdf.startswith(b"%PDF")
    assert b"DejaVu" in pdf
