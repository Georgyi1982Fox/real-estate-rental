"""Подробный разбор риска (TASK-094)."""

import pytest

from bina.application.fraud import FraudLevel
from bina.application.localization import script_of
from bina.application.ports.fraud import REASONS
from bina.application.risk_report import risk_report


@pytest.mark.parametrize("language", ["ru", "en", "ka"])
def test_every_reason_has_text_in_every_language(language: str) -> None:
    report = risk_report(90, sorted(REASONS), language)
    assert report.level is FraudLevel.HIGH
    assert [code for code, _ in report.reasons] == sorted(REASONS)
    for _, text in report.reasons:
        assert text.title and text.explanation and text.check
    # Совет по каждой причине + 4 общих
    assert len(report.checklist) == len(REASONS) + 4


def test_texts_in_the_right_script() -> None:
    for language in ("ru", "en", "ka"):
        report = risk_report(50, sorted(REASONS), language)
        for _, text in report.reasons:
            assert script_of(text.explanation) == language, text.explanation
        assert all(script_of(item) == language for item in report.checklist)


def test_unknown_codes_and_language() -> None:
    report = risk_report(10, ["prepayment", "prepayment", "made_up"], "de")
    assert report.level is FraudLevel.NONE
    assert [code for code, _ in report.reasons] == ["prepayment"]
    assert report.reasons[0][1].title == "Asks for prepayment"


def test_no_reasons_still_has_general_advice() -> None:
    report = risk_report(0, [], "ru")
    assert report.reasons == []
    assert len(report.checklist) == 4
