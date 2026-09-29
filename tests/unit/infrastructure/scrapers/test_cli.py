from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from bina.application.use_cases.check_fraud import FraudStats
from bina.application.use_cases.notifications import CreatedNotifications, DeliveryStats
from bina.application.use_cases.translate_listings import TranslationStats
from bina.infrastructure.scrapers import cli as scrape_cli
from bina.infrastructure.scrapers.backfill import BackfillStats
from bina.infrastructure.scrapers.pipeline import ScrapeResult


@pytest.fixture
def scrape(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(return_value=[ScrapeResult("myhome", 3, 2, 2, 2)])
    monkeypatch.setattr(scrape_cli, "scrape", mock)
    return mock


def test_source_is_required(scrape: AsyncMock) -> None:
    result = CliRunner().invoke(scrape_cli.cli, [])

    assert result.exit_code == 2
    assert "--source" in result.output
    scrape.assert_not_awaited()


def test_scrape_myhome(scrape: AsyncMock, tmp_path: Path) -> None:
    result = CliRunner().invoke(
        scrape_cli.cli,
        ["--source", "myhome", "--limit", "100", "--no-details", "--dump-dir", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert "сохранено 2" in result.output
    args: Any = scrape.await_args
    assert args.args == (["myhome"], 100)
    assert args.kwargs == {"details": False, "embeddings": False, "dump_dir": tmp_path}


def test_all_sources(scrape: AsyncMock) -> None:
    result = CliRunner().invoke(scrape_cli.cli, ["--source", "all"])

    assert result.exit_code == 0, result.output
    assert scrape.await_args is not None
    assert scrape.await_args.args[0] == ["myhome", "ss"]


@pytest.mark.parametrize("limit", ["0", "1001"])
def test_limit_bounds(scrape: AsyncMock, limit: str) -> None:
    result = CliRunner().invoke(scrape_cli.cli, ["--source", "myhome", "--limit", limit])
    assert result.exit_code == 2


NO_NOTIFICATIONS = CreatedNotifications(new_listings=0, price_drops=0)


class OneShotScheduler:
    """Вместо APScheduler: запускает задачу один раз и завершает команду."""

    instances: ClassVar[list["OneShotScheduler"]] = []

    def __init__(self, job: Any, interval_hours: int) -> None:
        self.job = job
        self.interval_hours = interval_hours
        self.stopped = False
        OneShotScheduler.instances.append(self)

    def start(self) -> None:
        pass

    async def stop(self) -> None:
        self.stopped = True


NO_FRAUD = FraudStats(checked=0, suspicious=0, hidden=0, failed=0)
NO_DETAILS = BackfillStats(checked=0, updated=0, archived=0, failed=0)


def run_schedule(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> Any:
    """Вызывает ``schedule``: вместо вечного ожидания один раз выполняет задачу."""
    OneShotScheduler.instances.clear()
    monkeypatch.setattr(scrape_cli, "ScraperScheduler", OneShotScheduler)

    class Event:
        async def wait(self) -> None:
            await OneShotScheduler.instances[-1].job()

    monkeypatch.setattr("bina.infrastructure.scrapers.cli.asyncio.Event", Event)
    if not isinstance(getattr(scrape_cli, "notify"), AsyncMock):
        monkeypatch.setattr(scrape_cli, "notify", AsyncMock(return_value=(NO_NOTIFICATIONS, None)))
    if not isinstance(getattr(scrape_cli, "fill_details"), AsyncMock):
        monkeypatch.setattr(scrape_cli, "fill_details", AsyncMock(return_value=NO_DETAILS))
    if not isinstance(getattr(scrape_cli, "check_fraud"), AsyncMock):
        monkeypatch.setattr(scrape_cli, "check_fraud", AsyncMock(return_value=NO_FRAUD))
    return CliRunner().invoke(scrape_cli.cli, ["schedule", *args])


def test_schedule_runs_all_sources_and_prints_results(
    scrape: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = run_schedule(monkeypatch, ["--interval", "3", "--limit", "20"])

    assert result.exit_code == 0, result.output
    scheduler = OneShotScheduler.instances[-1]
    assert scheduler.interval_hours == 3
    assert scheduler.stopped
    args: Any = scrape.await_args
    assert args.args == (["myhome", "ss"], 20)
    assert "следующий через 3 ч" in result.output
    assert "myhome: найдено 3" in result.output


def test_schedule_survives_failed_run(scrape: AsyncMock, monkeypatch: pytest.MonkeyPatch) -> None:
    scrape.side_effect = RuntimeError("db down")

    result = run_schedule(monkeypatch, [])

    assert result.exit_code == 0, result.output
    assert "найдено" not in result.output


def test_translate_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    translate = AsyncMock()
    monkeypatch.setattr(scrape_cli, "translate", translate)

    result = CliRunner().invoke(scrape_cli.cli, ["translate"])

    assert result.exit_code == 1
    assert "LLM_API_KEY" in result.output
    translate.assert_not_awaited()


def test_translate_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    translate = AsyncMock(return_value=TranslationStats(checked=5, translated=4, failed=1))
    monkeypatch.setattr(scrape_cli, "translate", translate)

    result = CliRunner().invoke(scrape_cli.cli, ["translate", "--limit", "5"])

    assert result.exit_code == 0, result.output
    translate.assert_awaited_once_with(5)
    assert "переведено 4, ошибок 1" in result.output


def test_translate_command_when_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    translate = AsyncMock(side_effect=scrape_cli.TranslationBusyError("busy"))
    monkeypatch.setattr(scrape_cli, "translate", translate)

    result = CliRunner().invoke(scrape_cli.cli, ["translate"])

    assert result.exit_code == 1
    assert "перевод уже идёт" in result.output


def test_languages_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scrape_cli, "language_status", AsyncMock(return_value=(120, 7)))

    result = CliRunner().invoke(scrape_cli.cli, ["languages"])

    assert result.exit_code == 0, result.output
    assert "объявлений 120, на всех трёх языках 113, ждут перевода 7" in result.output
    assert "translate --limit 5000" in result.output


def test_details_command(monkeypatch: pytest.MonkeyPatch) -> None:
    fill = AsyncMock(return_value=BackfillStats(checked=5, updated=4, archived=1, failed=0))
    monkeypatch.setattr(scrape_cli, "fill_details", fill)

    result = CliRunner().invoke(scrape_cli.cli, ["details", "--limit", "5", "--recheck-days", "2"])

    assert result.exit_code == 0, result.output
    fill.assert_awaited_once_with(5, 2)
    assert "обновлено 4, снято с сайта 1" in result.output


def test_fraud_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    check = AsyncMock(return_value=FraudStats(checked=7, suspicious=2, hidden=1, failed=0))
    monkeypatch.setattr(scrape_cli, "check_fraud", check)

    result = CliRunner().invoke(scrape_cli.cli, ["fraud", "--limit", "7"])

    assert result.exit_code == 0, result.output
    check.assert_awaited_once_with(7)
    assert "подозрительных 2, скрыто 1" in result.output

    monkeypatch.delenv("LLM_API_KEY")
    assert CliRunner().invoke(scrape_cli.cli, ["fraud"]).exit_code == 1


def test_schedule_translates_after_scraping(
    scrape: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    translate = AsyncMock(return_value=TranslationStats(checked=2, translated=2, failed=0))
    monkeypatch.setattr(scrape_cli, "translate", translate)

    calls: list[str] = []

    async def fake_translate(limit: int) -> TranslationStats:
        calls.append("translate")
        return TranslationStats(checked=2, translated=2, failed=0)

    async def fake_details(limit: int, recheck_days: int = 0) -> BackfillStats:
        calls.append("details")
        return BackfillStats(checked=3, updated=2, archived=1, failed=0)

    async def fake_fraud(limit: int) -> FraudStats:
        calls.append("fraud")
        return NO_FRAUD

    async def fake_notify() -> tuple[CreatedNotifications, None]:
        calls.append("notify")
        return NO_NOTIFICATIONS, None

    translate.side_effect = fake_translate
    check = AsyncMock(side_effect=fake_fraud)
    monkeypatch.setattr(scrape_cli, "check_fraud", check)
    monkeypatch.setattr(scrape_cli, "fill_details", AsyncMock(side_effect=fake_details))
    monkeypatch.setattr(scrape_cli, "notify", AsyncMock(side_effect=fake_notify))

    result = run_schedule(monkeypatch, ["--translate-limit", "30", "--fraud-limit", "40"])

    assert result.exit_code == 0, result.output
    translate.assert_awaited_once_with(30)
    check.assert_awaited_once_with(40)
    # Проверка на мошенничество — до уведомлений
    assert calls == ["details", "translate", "fraud", "notify"]
    assert "подробности: проверено 3, обновлено 2, снято с сайта 1" in result.output
    assert "перевод: проверено 2, переведено 2" in result.output
    assert "антифрод: проверено 0" in result.output


def test_schedule_without_key_only_scrapes(
    scrape: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    translate = AsyncMock()
    monkeypatch.setattr(scrape_cli, "translate", translate)

    result = run_schedule(monkeypatch, [])

    assert result.exit_code == 0, result.output
    assert "перевод отключён" in result.output
    translate.assert_not_awaited()


class FakeUseCase:
    """Вместо TranslateListingsUseCase: заданные итоги по пачкам."""

    batches: ClassVar[list[TranslationStats]] = []
    limits: ClassVar[list[int]] = []

    def __init__(
        self, translator: Any, repository: Any, after_save: Any = None, concurrency: int = 1
    ) -> None:
        pass

    async def execute(self, limit: int) -> TranslationStats:
        FakeUseCase.limits.append(limit)
        return FakeUseCase.batches.pop(0)


class FakeDb:
    engine = None

    def __init__(self) -> None:
        self.sessions: list[AsyncMock] = []

    def session_factory(self) -> Any:
        session = AsyncMock()
        self.sessions.append(session)

        class Context:
            async def __aenter__(self) -> AsyncMock:
                return session

            async def __aexit__(self, *args: object) -> None:
                return None

        return Context()

    async def dispose(self) -> None:
        pass


async def test_translate_commits_in_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeDb()
    provider = AsyncMock()
    monkeypatch.setattr(scrape_cli, "DatabaseManager", lambda: db)
    monkeypatch.setattr(
        "bina.infrastructure.scrapers.cli.LLMFactory.create_provider",
        staticmethod(lambda: provider),
    )
    monkeypatch.setattr(scrape_cli, "TranslateListingsUseCase", FakeUseCase)

    @asynccontextmanager
    async def free_lock(engine: Any, key: int) -> AsyncIterator[bool]:
        yield True

    monkeypatch.setattr(scrape_cli, "advisory_lock", free_lock)
    FakeUseCase.limits.clear()
    FakeUseCase.batches[:] = [
        TranslationStats(checked=10, translated=9, failed=1),
        TranslationStats(checked=10, translated=10, failed=0),
        TranslationStats(checked=3, translated=0, failed=3),  # дальше только ошибки — стоп
    ]

    stats = await scrape_cli.translate(25)

    assert FakeUseCase.limits == [20, 15, 5]
    assert stats == TranslationStats(checked=23, translated=19, failed=4)
    assert all(session.commit.await_count == 1 for session in db.sessions)
    provider.close.assert_awaited_once()


def test_notify_command(monkeypatch: pytest.MonkeyPatch) -> None:
    notify = AsyncMock(
        return_value=(
            CreatedNotifications(new_listings=3, price_drops=1),
            DeliveryStats(sent=3, skipped=1, failed=0),
        )
    )
    monkeypatch.setattr(scrape_cli, "notify", notify)

    result = CliRunner().invoke(scrape_cli.cli, ["notify"])

    assert result.exit_code == 0, result.output
    assert "новых квартир 3, снижений цены 1; отправлено 3, пропущено 1" in result.output


def test_notify_command_without_bot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scrape_cli, "notify", AsyncMock(return_value=(NO_NOTIFICATIONS, None)))

    result = CliRunner().invoke(scrape_cli.cli, ["notify"])

    assert "не отправлены (нет BOT_TOKEN)" in result.output


def test_schedule_creates_notifications_even_if_scrape_fails(
    scrape: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    scrape.side_effect = RuntimeError("site down")
    notify = AsyncMock(return_value=(CreatedNotifications(new_listings=2, price_drops=0), None))
    monkeypatch.setattr(scrape_cli, "notify", notify)

    result = run_schedule(monkeypatch, [])

    assert result.exit_code == 0, result.output
    notify.assert_awaited_once()
    assert "новых квартир 2" in result.output
