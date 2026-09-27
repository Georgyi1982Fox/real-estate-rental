from pathlib import Path
from typing import Any
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
