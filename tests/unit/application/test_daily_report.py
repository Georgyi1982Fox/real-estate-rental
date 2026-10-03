"""Когда присылать ежедневный отчёт владельцу (TASK-041)."""

from datetime import UTC, date, datetime

import pytest

from bina.application.daily_report import report_day, report_hour


def test_report_after_hour_in_tbilisi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DAILY_REPORT", raising=False)
    monkeypatch.delenv("DAILY_REPORT_HOUR", raising=False)
    assert report_hour() == 9
    # 04:30 UTC = 08:30 Тбилиси — ещё рано; 05:00 UTC = 09:00 — пора
    assert report_day(datetime(2026, 10, 3, 4, 30, tzinfo=UTC)) is None
    assert report_day(datetime(2026, 10, 3, 5, 0, tzinfo=UTC)) == date(2026, 10, 3)
    # 21:00 UTC = 01:00 следующего дня в Тбилиси: отчёт за новый день ещё рано
    assert report_day(datetime(2026, 10, 3, 21, 0, tzinfo=UTC)) is None


def test_report_hour_and_switch_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DAILY_REPORT_HOUR", "20")
    assert report_day(datetime(2026, 10, 3, 15, 0, tzinfo=UTC)) is None
    assert report_day(datetime(2026, 10, 3, 16, 0, tzinfo=UTC)) == date(2026, 10, 3)
    monkeypatch.setenv("DAILY_REPORT_HOUR", "99")
    assert report_hour() == 9
    monkeypatch.setenv("DAILY_REPORT", "0")
    assert report_day(datetime(2026, 10, 3, 16, 0, tzinfo=UTC)) is None
