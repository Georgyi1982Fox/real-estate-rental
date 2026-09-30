"""Наблюдение за работой парсера и сервисов (TASK-043).

Копит состояние между запусками расписания и решает, о чём написать владельцу:
- шаг запуска упал (парсинг, перевод, уведомления…) — сразу;
- источник два запуска подряд не дал ни одного объявления (сайт изменился или
  блокирует парсер);
- сервер Mini App не отвечает.

Об одной и той же проблеме — не чаще раза в ``REPEAT_EVERY``; когда проблема ушла —
сообщение «снова работает».
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

EMPTY_RUNS_TO_ALERT = 2
REPEAT_EVERY = timedelta(hours=6)
MAX_ERROR_LENGTH = 200


@dataclass(frozen=True, slots=True)
class Alert:
    """Что написать: ключ текста и подстановки."""

    text: str
    params: dict[str, str | int]


@dataclass
class HealthMonitor:
    _problems: dict[str, datetime] = field(default_factory=dict)  # ключ → когда писали
    _empty_runs: dict[str, int] = field(default_factory=dict)
    _pending: list[Alert] = field(default_factory=list)

    def _problem(self, key: str, alert: Alert, now: datetime) -> None:
        last = self._problems.get(key)
        if last is None or now - last >= REPEAT_EVERY:
            self._problems[key] = now
            self._pending.append(alert)

    def _recovered(self, key: str, alert: Alert) -> None:
        if self._problems.pop(key, None) is not None:
            self._pending.append(alert)

    def step_failed(self, step: str, error: str, now: datetime) -> None:
        text = error.strip()[:MAX_ERROR_LENGTH] or "error"
        self._problem(
            f"step:{step}", Alert("alert_step_failed", {"step": step, "error": text}), now
        )

    def step_ok(self, step: str) -> None:
        self._recovered(f"step:{step}", Alert("alert_step_ok", {"step": step}))

    def source_result(self, source: str, scraped: int, now: datetime) -> None:
        key = f"source:{source}"
        if scraped > 0:
            self._empty_runs[source] = 0
            self._recovered(key, Alert("alert_source_ok", {"source": source, "count": scraped}))
            return
        runs = self._empty_runs.get(source, 0) + 1
        self._empty_runs[source] = runs
        if runs >= EMPTY_RUNS_TO_ALERT:
            self._problem(key, Alert("alert_source_empty", {"source": source, "runs": runs}), now)

    def api_health(self, error: str | None, now: datetime) -> None:
        if error is None:
            self._recovered("api", Alert("alert_api_ok", {}))
        else:
            self._problem("api", Alert("alert_api_down", {"error": error[:MAX_ERROR_LENGTH]}), now)

    def collect(self) -> list[Alert]:
        """Накопленные сообщения (и очистить очередь)."""
        alerts, self._pending = self._pending, []
        return alerts
