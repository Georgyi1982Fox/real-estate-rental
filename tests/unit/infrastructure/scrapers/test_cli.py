from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from bina.infrastructure.scrapers import cli as scrape_cli
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


def run_schedule(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> Any:
    """Вызывает ``schedule``: вместо вечного ожидания один раз выполняет задачу."""
    OneShotScheduler.instances.clear()
    monkeypatch.setattr(scrape_cli, "ScraperScheduler", OneShotScheduler)

    class Event:
        async def wait(self) -> None:
            await OneShotScheduler.instances[-1].job()

    monkeypatch.setattr("bina.infrastructure.scrapers.cli.asyncio.Event", Event)
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
