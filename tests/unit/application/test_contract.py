"""Пункты двуязычного договора аренды (TASK-101)."""

from datetime import date
from decimal import Decimal

import pytest

from bina.application.contract import (
    ContractData,
    Utilities,
    contract_clauses,
    signature_labels,
)
from bina.application.localization import script_of


def data(**changes: object) -> ContractData:
    values: dict[str, object] = {
        "landlord_name": "Giorgi Beridze",
        "tenant_name": "Anna Smith",
        "address": "Chavchavadze Ave 10, apt 5",
        "rooms": 2,
        "area": 60.5,
        "start": date(2026, 11, 1),
        "months": 12,
        "rent": Decimal(1500),
        "currency": "GEL",
        "deposit": Decimal(1500),
        "payment_day": 5,
        "utilities": Utilities.TENANT,
        "pets_allowed": False,
    }
    values.update(changes)
    return ContractData(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("second", ["ru", "en"])
def test_each_column_is_fully_in_its_language(second: str) -> None:
    rows = contract_clauses(data(), second)
    assert len(rows) == 11
    for ka, other in rows:
        assert script_of(ka) == "ka"
        assert script_of(other) == second
        # Номер пункта совпадает в обеих колонках
        assert ka.split(".")[0] == other.split(".")[0]


def test_values_are_filled_in() -> None:
    rows = contract_clauses(data(), "en")
    text = " ".join(other for _, other in rows)
    for expected in (
        "Giorgi Beridze",
        "Anna Smith",
        "Chavchavadze Ave 10, apt 5",
        "60.5 m²",
        "01.11.2026",
        "12 months",
        "1 500 GEL",
        "by day 5",
        "Pets are not allowed",
        "paid by the Tenant",
    ):
        assert expected in text
    ka = " ".join(ka for ka, _ in rows)
    assert "1 500 ლარი" in ka
    assert "01.11.2026" in ka


def test_russian_currency_and_options() -> None:
    rows = contract_clauses(
        data(currency="USD", pets_allowed=True, utilities=Utilities.INCLUDED), "ru"
    )
    text = " ".join(other for _, other in rows)
    assert "1 500 долларов США" in text
    assert "разрешено" in text
    assert "включены в арендную плату" in text


def test_ids_and_notes() -> None:
    rows = contract_clauses(
        data(landlord_id="01001012345", tenant_id="P1234567", notes="Parking space included"),
        "en",
    )
    assert len(rows) == 12
    assert "passport / ID: 01001012345" in rows[0][1]
    assert "P1234567" in rows[0][0]
    assert rows[11][1] == "12. Additional terms. Parking space included"


def test_unknown_second_language() -> None:
    with pytest.raises(ValueError):
        contract_clauses(data(), "de")


def test_signature_labels() -> None:
    (landlord_ka, landlord_other), (tenant_ka, tenant_other) = signature_labels("en")
    assert (landlord_other, tenant_other) == ("Landlord", "Tenant")
    assert script_of(landlord_ka) == script_of(tenant_ka) == "ka"
