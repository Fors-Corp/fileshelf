from __future__ import annotations

from typer.testing import CliRunner

from fileshelf.cli import app


def test_help_has_single_support_line() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert result.stdout.count("Support this project: https://marcfors.com/donate?from=fileshelf") == 1
