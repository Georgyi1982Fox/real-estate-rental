from pathlib import Path

from click.testing import CliRunner

from bina.infrastructure.db.seed import cli


def test_missing_file_is_reported(tmp_path: Path) -> None:
    result = CliRunner().invoke(cli, ["--file", str(tmp_path / "nope.json")])

    assert result.exit_code == 1
    assert "не найден" in result.output
