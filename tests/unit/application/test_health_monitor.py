"""Наблюдение за сбоями (TASK-043): когда писать владельцу."""

from datetime import UTC, datetime, timedelta

from bina.application.health_monitor import HealthMonitor

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)


def texts(monitor: HealthMonitor) -> list[str]:
    return [alert.text for alert in monitor.collect()]


def test_step_failure_repeat_and_recovery() -> None:
    monitor = HealthMonitor()
    monitor.step_failed("translate", "LLM timeout", NOW)
    [alert] = monitor.collect()
    assert (alert.text, alert.params) == (
        "alert_step_failed",
        {"step": "translate", "error": "LLM timeout"},
    )
    monitor.step_failed("translate", "LLM timeout", NOW + timedelta(hours=1))
    assert texts(monitor) == [], "не чаще раза в 6 часов"
    monitor.step_failed("translate", "LLM timeout", NOW + timedelta(hours=6))
    assert texts(monitor) == ["alert_step_failed"]
    monitor.step_ok("translate")
    assert texts(monitor) == ["alert_step_ok"]
    monitor.step_ok("translate")
    assert texts(monitor) == [], "«снова работает» — один раз"
    monitor.step_ok("notify")
    assert texts(monitor) == [], "о шаге без сбоя не пишем"


def test_empty_source_needs_two_runs() -> None:
    monitor = HealthMonitor()
    monitor.source_result("ss", 0, NOW)
    assert texts(monitor) == []
    monitor.source_result("ss", 0, NOW + timedelta(hours=1))
    [alert] = monitor.collect()
    assert (alert.text, alert.params) == ("alert_source_empty", {"source": "ss", "runs": 2})
    monitor.source_result("myhome", 0, NOW)
    monitor.source_result("ss", 120, NOW + timedelta(hours=2))
    [recovered] = monitor.collect()
    assert (recovered.text, recovered.params) == ("alert_source_ok", {"source": "ss", "count": 120})


def test_api_health_and_long_errors() -> None:
    monitor = HealthMonitor()
    monitor.api_health(None, NOW)
    assert texts(monitor) == []
    monitor.api_health("Connection refused", NOW)
    assert texts(monitor) == ["alert_api_down"]
    monitor.api_health(None, NOW)
    assert texts(monitor) == ["alert_api_ok"]
    monitor.step_failed("scrape", "x" * 1000, NOW)
    [alert] = monitor.collect()
    assert len(str(alert.params["error"])) == 200
